"""Backing up and restoring CrossPatch's settings (config, profiles, ignored conflicts).

A backup is a zip holding the settings files plus a small manifest. Only
settings are saved, never mods: those live in the mods folder and can be
downloaded again, profiles cannot.

Automatic backups land in <CONFIG_DIR>/backups and are pruned to the most
recent few, so they cannot slowly fill the disk.
"""

import datetime
import json
import os
import zipfile

from Config import CONFIG_DIR
from Constants import APP_VERSION

BACKUP_DIR = os.path.join(CONFIG_DIR, "backups")
FILE_EXTENSION = ".zip"
MANIFEST_NAME = "manifest.json"
# The only entries ever read back from a backup. Anything else in the zip is
# ignored, so a crafted archive cannot write outside the config folder.
SETTINGS_FILES = ("config.json", "ignored_conflicts.json")
KEEP_AUTOMATIC = 10


def _timestamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def suggested_file_name():
    return f"CrossPatch-settings-{_timestamp()}{FILE_EXTENSION}"


def create_backup(dest_path, reason="manual"):
    """Writes the settings to dest_path. Returns the number of files saved."""
    saved = 0
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in SETTINGS_FILES:
            path = os.path.join(CONFIG_DIR, name)
            if os.path.isfile(path):
                zf.write(path, name)
                saved += 1
        manifest = {
            "app_version": APP_VERSION,
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
        }
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
    return saved


def read_backup(path):
    """Validates a backup and returns {name: bytes} for the settings it holds.

    Raises ValueError when the file is not a CrossPatch backup, so nothing is
    half restored.
    """
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise ValueError("This file is not a zip archive.")

    with zf:
        names = set(zf.namelist())
        if "config.json" not in names:
            raise ValueError("This archive does not contain a CrossPatch config.json.")
        contents = {name: zf.read(name) for name in SETTINGS_FILES if name in names}

    try:
        config = json.loads(contents["config.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"The config.json in this backup is damaged: {e}")
    if not isinstance(config, dict):
        raise ValueError("The config.json in this backup is not a settings file.")
    return contents


def restore_backup(path):
    """Replaces the current settings with those in the backup.

    The current settings are backed up automatically first, so a restore can
    always be undone. Returns the path of that safety backup.
    """
    contents = read_backup(path)
    safety = auto_backup("before-restore")
    for name, data in contents.items():
        with open(os.path.join(CONFIG_DIR, name), "wb") as f:
            f.write(data)
    return safety


def auto_backup(reason):
    """Backs up into BACKUP_DIR and prunes old automatic backups."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, f"auto-{_timestamp()}-{reason}{FILE_EXTENSION}")
    create_backup(path, reason)
    prune(BACKUP_DIR, KEEP_AUTOMATIC)
    return path


def prune(directory, keep):
    """Deletes the oldest automatic backups beyond `keep`."""
    try:
        backups = sorted(
            (f for f in os.listdir(directory) if f.startswith("auto-") and f.endswith(FILE_EXTENSION)),
            reverse=True,
        )
    except FileNotFoundError:
        return
    for old in backups[keep:]:
        try:
            os.remove(os.path.join(directory, old))
        except OSError as e:
            print(f"Could not delete the old backup '{old}': {e}")
