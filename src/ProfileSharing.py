"""Sharing a profile between two installs of CrossPatch.

An exported profile is a small JSON document. It lists the mods by their
GameBanana page rather than carrying their content, so nothing is
redistributed: the person importing it always downloads the files from the
original author's page, in the load order the profile was exported with.

`build_export` turns a profile into that document, `read_export` reads one
back, and `plan_import` works out what the local install still has to do about
it. None of this touches Qt so it stays testable on its own.
"""

import json
import os
import re
import time

import Util

FORMAT_ID = "crosspatch-profile"
FORMAT_VERSION = 1
FILE_EXTENSION = ".crosspatch"

# What has to happen to a mod listed in an imported profile.
STATUS_INSTALLED = "installed"      # already on disk, nothing to do
STATUS_DOWNLOAD = "download"        # missing, but the page is known
STATUS_UNAVAILABLE = "unavailable"  # missing and no page to download it from

_ILLEGAL_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_folder_name(name, fallback="mod"):
    """Keeps a folder name from an exported profile usable on this system.

    The file may well have been written on another OS, so a name that is
    perfectly fine there can be rejected here.
    """
    name = os.path.basename((name or "").replace("\\", "/")).strip()
    name = _ILLEGAL_NAME_CHARS.sub("_", name).rstrip(". ")
    return name or fallback


def page_key(url):
    """Reduces a GameBanana URL to '<type>/<id>'.

    Two links to the same submission then compare equal whatever the slug or
    the protocol, which is how an imported mod is recognised as one that is
    already installed.
    """
    if not url:
        return None
    item_type, item_id = Util.get_gb_item_details_from_url(url)
    if not item_type or not item_id:
        return None
    return f"{item_type}/{item_id}"


def build_export(profile_name, profile_data, mods_folder, app_version):
    """Describes a profile as the dictionary that gets written to disk."""
    enabled = profile_data.get("enabled_mods") or {}
    priority = profile_data.get("mod_priority") or []
    configurations = profile_data.get("mod_configurations") or {}

    on_disk = set(Util.list_mod_folders(mods_folder))
    # The priority list carries the load order, so it comes first. A mod that
    # is on disk but never made it into that list is still worth exporting.
    ordered = [folder for folder in priority if folder in on_disk]
    ordered += sorted(folder for folder in on_disk if folder not in priority)

    mods = []
    for folder in ordered:
        info = Util.read_mod_info(os.path.join(mods_folder, folder))
        entry = {
            "folder": folder,
            "name": info.get("name") or folder,
            "version": info.get("version") or "",
            "author": info.get("author") or "",
            "mod_type": info.get("mod_type") or "pak",
            "mod_page": info.get("mod_page") or "",
            # Recorded on download since profile sharing landed, so an import
            # can pick the same archive again when a submission offers several.
            "source_file": info.get("source_file") or "",
            "enabled": bool(enabled.get(folder, False)),
        }
        if folder in configurations:
            entry["configuration"] = configurations[folder]
        mods.append(entry)

    return {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "app_version": app_version,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "profile_name": profile_name,
        "mods": mods,
    }


def write_export(path, payload):
    """Writes an export. newline='\\n' so the file reads the same everywhere."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def read_export(path):
    """Loads an export and refuses anything this version cannot make sense of.

    Raises ValueError with a message meant for the user.
    """
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict) or payload.get("format") != FORMAT_ID:
        raise ValueError("The file is not a CrossPatch profile.")

    try:
        version = int(payload.get("format_version", 0))
    except (TypeError, ValueError):
        raise ValueError("The file does not say which format version it uses.")
    if version > FORMAT_VERSION:
        raise ValueError(
            f"The file was written by a newer CrossPatch (format {version}, "
            f"this build understands {FORMAT_VERSION}). Update CrossPatch first."
        )

    if not isinstance(payload.get("mods"), list):
        raise ValueError("The file lists no mods.")

    return payload


def _installed_index(mods_folder):
    """Maps what is on disk, by folder name and by GameBanana page."""
    by_folder = {}
    by_page = {}
    for folder in Util.list_mod_folders(mods_folder):
        by_folder[folder.lower()] = folder
        key = page_key(Util.read_mod_info(os.path.join(mods_folder, folder)).get("mod_page"))
        if key and key not in by_page:
            by_page[key] = folder
    return by_folder, by_page


def _free_folder_name(base, taken):
    """Finds a folder name nothing uses yet: 'Mod', then 'Mod (2)', 'Mod (3)'."""
    base = _safe_folder_name(base)
    if base.lower() not in taken:
        return base
    index = 2
    while f"{base} ({index})".lower() in taken:
        index += 1
    return f"{base} ({index})"


def plan_import(payload, mods_folder):
    """Decides what to do with every mod the imported profile lists.

    Returns one entry per mod, in the profile's load order, each carrying the
    folder it will live in locally and the status the review dialog shows.
    """
    by_folder, by_page = _installed_index(mods_folder)
    taken = set(by_folder)

    entries = []
    for mod in payload.get("mods", []):
        if not isinstance(mod, dict):
            continue

        source_folder = _safe_folder_name(mod.get("folder") or mod.get("name") or "mod")
        key = page_key(mod.get("mod_page"))

        if key and key in by_page:
            local_folder = by_page[key]
            status = STATUS_INSTALLED
        else:
            same_name = by_folder.get(source_folder.lower())
            if same_name is not None:
                local_key = page_key(
                    Util.read_mod_info(os.path.join(mods_folder, same_name)).get("mod_page"))
                if key is None or local_key is None:
                    # Nothing to compare the two against, so a folder with the
                    # same name is taken to be the same mod. That is what the
                    # person importing would assume looking at the list.
                    local_folder = same_name
                    status = STATUS_INSTALLED
                else:
                    # Same folder name but a different submission. The incoming
                    # mod gets its own folder rather than overwriting a mod the
                    # user already has.
                    local_folder = _free_folder_name(source_folder, taken)
                    status = STATUS_DOWNLOAD
            else:
                local_folder = source_folder
                status = STATUS_DOWNLOAD if key else STATUS_UNAVAILABLE

        if status == STATUS_DOWNLOAD and not key:
            status = STATUS_UNAVAILABLE

        taken.add(local_folder.lower())
        entries.append({
            "source_folder": source_folder,
            "local_folder": local_folder,
            "name": mod.get("name") or source_folder,
            "author": mod.get("author") or "",
            "version": mod.get("version") or "",
            "mod_page": mod.get("mod_page") or "",
            "source_file": mod.get("source_file") or "",
            "enabled": bool(mod.get("enabled", False)),
            "configuration": mod.get("configuration"),
            "status": status,
            # Both are filled in while the import runs.
            "skipped": status == STATUS_UNAVAILABLE,
            "error": "",
        })

    return entries


def pick_file(entry, item_data):
    """Chooses which archive of a submission matches the exported mod.

    Returns None when the choice is genuinely ambiguous, in which case the
    caller has to ask. Guessing there would silently install the wrong variant
    of a mod that ships one archive per character or per language.
    """
    files = [f for f in (item_data.get("_aFiles") or []) if f.get("_sDownloadUrl")]
    if not files:
        return None

    wanted_file = (entry.get("source_file") or "").strip().lower()
    if wanted_file:
        exact = [f for f in files if (f.get("_sFile") or "").strip().lower() == wanted_file]
        if len(exact) == 1:
            return exact[0]

    if len(files) == 1:
        return files[0]

    wanted_version = (entry.get("version") or "").strip().lower()
    if wanted_version:
        same_version = [f for f in files
                        if (f.get("_sVersion") or "").strip().lower() == wanted_version]
        if len(same_version) == 1:
            return same_version[0]

    return None


def profile_from_entries(entries):
    """Builds the profile data out of the entries that ended up installed."""
    enabled_mods = {}
    mod_priority = []
    mod_configurations = {}

    for entry in entries:
        if entry.get("skipped"):
            continue
        folder = entry["local_folder"]
        mod_priority.append(folder)
        enabled_mods[folder] = bool(entry.get("enabled", False))
        if entry.get("configuration"):
            mod_configurations[folder] = entry["configuration"]

    return {
        "enabled_mods": enabled_mods,
        "mod_priority": mod_priority,
        "mod_configurations": mod_configurations,
    }


def suggested_file_name(profile_name):
    """A file name that is safe to write and says which profile it holds.

    Separators become underscores first: a profile called 'Sonic / Shadow'
    should keep both halves, where _safe_folder_name would take the basename
    and leave 'Shadow'.
    """
    flattened = (profile_name or "").replace("\\", "_").replace("/", "_")
    return f"{_safe_folder_name(flattened, 'profile')}{FILE_EXTENSION}"
