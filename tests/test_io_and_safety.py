"""Protocol links, archive extraction, update digests, backups, logs, locales."""

import glob
import hashlib
import json
import os
import re
import zipfile

import pytest

import Backup
import Logs
import ProfileSharing
import ProtocolLinks
import Util
from Updater import verify_digest
from conftest import ROOT


# --- crosspatch: links ---------------------------------------------------

def test_schema_link_is_parsed():
    link = ProtocolLinks.parse("crosspatch:https://gamebanana.com/dl/1828304,Mod,721344,zip")
    assert link == {
        "kind": "schema",
        "download_url": "https://gamebanana.com/dl/1828304",
        "item_type": "Mod",
        "item_id": "721344",
        "file_ext": "zip",
        "page_url": "https://gamebanana.com/mods/721344",
    }


def test_schema_link_with_double_slash_and_default_ext():
    link = ProtocolLinks.parse("crosspatch://https://files.gamebanana.com/mods/x.7z,Sound,12")
    assert link["download_url"] == "https://files.gamebanana.com/mods/x.7z"
    assert link["file_ext"] == "zip"


def test_page_link_is_parsed_and_decoded():
    link = ProtocolLinks.parse("crosspatch://install?url=https%3A%2F%2Fgamebanana.com%2Fmods%2F5")
    assert link == {"kind": "page", "page_url": "https://gamebanana.com/mods/5"}


@pytest.mark.parametrize("url", [
    "crosspatch:https://evil.example/payload.zip,Mod,1,zip",
    "crosspatch:https://gamebanana.com.evil.example/x,Mod,1,zip",
    "crosspatch:http://gamebanana.com/dl/1,Mod,1,zip",
    "crosspatch:https://gamebanana.com/dl/1,Mod,1;rm,zip",
    "crosspatch:https://gamebanana.com/dl/1,../../x,1,zip",
    "crosspatch:https://gamebanana.com/dl/1,Mod,1,exe",
    "crosspatch:https://gamebanana.com/dl/1,Mod",
    "crosspatch://install?url=https://evil.example/mods/1",
    "https://gamebanana.com/mods/1",
])
def test_bad_links_are_refused(url):
    with pytest.raises(ValueError):
        ProtocolLinks.parse(url)


# --- archive extraction --------------------------------------------------

def _zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def test_single_top_folder_is_flattened(tmp_path):
    archive = tmp_path / "mod.zip"
    _zip(archive, {"MyMod/MyMod_P.pak": b"pak", "MyMod/readme.txt": b"hi"})
    dest = tmp_path / "out"
    Util.extract_archive(str(archive), str(dest))
    assert sorted(os.listdir(dest)) == ["MyMod_P.pak", "readme.txt"]


def test_folder_containing_its_own_name_is_flattened(tmp_path):
    # The Linux release zip is CrossPatch/CrossPatch: the binary has the same
    # name as its folder, which used to make the flattening collide.
    archive = tmp_path / "release.zip"
    _zip(archive, {"CrossPatch/CrossPatch": b"elf", "CrossPatch/_internal/lib.so": b"so"})
    dest = tmp_path / "out"
    Util.extract_archive(str(archive), str(dest))
    assert os.path.isfile(dest / "CrossPatch")
    assert os.path.isfile(dest / "_internal" / "lib.so")


def test_zip_entries_cannot_escape_the_destination(tmp_path):
    archive = tmp_path / "evil.zip"
    _zip(archive, {"../escaped.txt": b"x", "ok.txt": b"y"})
    dest = tmp_path / "out"
    Util.extract_archive(str(archive), str(dest))
    assert not (tmp_path / "escaped.txt").exists()


REAL_RELEASES = sorted(glob.glob(os.path.join(ROOT, "dist", "CrossPatch*.zip")))


@pytest.mark.skipif(not REAL_RELEASES, reason="no release zip in dist/")
@pytest.mark.parametrize("archive", REAL_RELEASES, ids=os.path.basename)
def test_real_release_zips_extract_to_an_app_folder(tmp_path, archive):
    dest = tmp_path / "out"
    Util.extract_archive(archive, str(dest))
    names = os.listdir(dest)
    assert "_internal" in names
    assert "CrossPatch.exe" in names or os.path.isfile(dest / "CrossPatch")


# --- update digest -------------------------------------------------------

def test_verify_digest(tmp_path):
    path = tmp_path / "update.zip"
    path.write_bytes(b"release")
    good = "sha256:" + hashlib.sha256(b"release").hexdigest()
    verify_digest(str(path), good)
    verify_digest(str(path), "sha256:" + hashlib.sha256(b"release").hexdigest().upper())
    verify_digest(str(path), "")  # older releases carry no digest
    with pytest.raises(RuntimeError):
        verify_digest(str(path), "sha256:" + "0" * 64)


# --- settings backups ----------------------------------------------------

def _write_config(data):
    with open(os.path.join(Backup.CONFIG_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)


def _read_config():
    with open(os.path.join(Backup.CONFIG_DIR, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def test_backup_and_restore_round_trip(tmp_path):
    _write_config({"profiles": {"Default": {"mod_priority": ["A"]}}})
    backup = tmp_path / "settings.zip"
    assert Backup.create_backup(str(backup)) >= 1

    _write_config({"profiles": {}})
    safety = Backup.restore_backup(str(backup))
    assert _read_config() == {"profiles": {"Default": {"mod_priority": ["A"]}}}
    # The settings that were replaced are kept aside.
    assert os.path.isfile(safety)


def test_restore_refuses_foreign_archives(tmp_path):
    no_config = tmp_path / "other.zip"
    _zip(no_config, {"something.txt": b"x"})
    with pytest.raises(ValueError):
        Backup.read_backup(str(no_config))

    damaged = tmp_path / "damaged.zip"
    _zip(damaged, {"config.json": b"{not json"})
    with pytest.raises(ValueError):
        Backup.read_backup(str(damaged))

    not_zip = tmp_path / "plain.zip"
    not_zip.write_bytes(b"not a zip")
    with pytest.raises(ValueError):
        Backup.read_backup(str(not_zip))


def test_restore_ignores_unexpected_entries(tmp_path):
    archive = tmp_path / "crafted.zip"
    _zip(archive, {"config.json": b"{}", "../outside.txt": b"x", "evil.dll": b"x"})
    assert set(Backup.read_backup(str(archive))) == {"config.json"}


def test_prune_keeps_the_newest_automatic_backups(tmp_path):
    for i in range(5):
        (tmp_path / f"auto-2026010{i}-000000-x.zip").write_bytes(b"")
    (tmp_path / "manual.zip").write_bytes(b"")
    Backup.prune(str(tmp_path), 2)
    assert sorted(os.listdir(tmp_path)) == [
        "auto-20260103-000000-x.zip", "auto-20260104-000000-x.zip", "manual.zip"]


# --- vanilla launch ------------------------------------------------------

def test_uninstall_all_mods_only_touches_managed_folders(tmp_path):
    game = tmp_path / "game"
    paks = game / "UNION" / "Content" / "Paks" / "~mods"
    ue4ss = tmp_path / "ue4ss_mods"
    mods = tmp_path / "mods"
    for folder in (paks / "000.ModA", paks / "001.ModB", paks / "UserOwnMod",
                   ue4ss / "ScriptMod", ue4ss / "BPModLoaderMod", mods / "ModA", mods / "ScriptMod"):
        folder.mkdir(parents=True)
    cfg = {"game_root": str(game), "mods_folder": str(mods),
           "ue4ss_mods_folder": str(ue4ss), "ue4ss_logic_mods_folder": ""}

    assert Util.uninstall_all_mods(cfg) == 3
    assert sorted(os.listdir(paks)) == ["UserOwnMod"]
    # UE4SS's own mods are not CrossPatch's to remove.
    assert sorted(os.listdir(ue4ss)) == ["BPModLoaderMod"]


# --- profile sharing file choice (reused by Update all) ------------------

def test_pick_file_prefers_source_file_then_version():
    files = [
        {"_sFile": "mod_v1.zip", "_sVersion": "1.0", "_sDownloadUrl": "u1"},
        {"_sFile": "mod_v2.zip", "_sVersion": "2.0", "_sDownloadUrl": "u2"},
    ]
    item = {"_aFiles": files}
    assert ProfileSharing.pick_file({"source_file": "MOD_V1.zip"}, item) is files[0]
    assert ProfileSharing.pick_file({"source_file": "gone.zip", "version": "2.0"}, item) is files[1]
    assert ProfileSharing.pick_file({"source_file": "", "version": "3.0"}, item) is None


# --- log file ------------------------------------------------------------

def test_log_rotation_keeps_previous_sessions(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "crosspatch.log").write_text("session 2")
    (logs / "crosspatch.1.log").write_text("session 1")
    Logs._rotate(str(logs))
    assert (logs / "crosspatch.1.log").read_text() == "session 2"
    assert (logs / "crosspatch.2.log").read_text() == "session 1"
    assert not (logs / "crosspatch.log").exists()


# --- locales -------------------------------------------------------------

def _load_locale(code):
    with open(os.path.join(ROOT, "assets", "locales", f"{code}.json"), encoding="utf-8") as f:
        return json.load(f)


def _placeholders(text):
    return set(re.findall(r"{(\w+)}", text))


def test_every_locale_has_the_same_keys_and_placeholders():
    english = _load_locale("en")
    for path in glob.glob(os.path.join(ROOT, "assets", "locales", "*.json")):
        code = os.path.splitext(os.path.basename(path))[0]
        other = _load_locale(code)
        missing = sorted(set(english) - set(other))
        extra = sorted(set(other) - set(english))
        assert not missing, f"{code}.json is missing {missing}"
        assert not extra, f"{code}.json has unknown keys {extra}"
        for key, text in english.items():
            if isinstance(text, str):
                assert _placeholders(text) == _placeholders(other[key]), f"{code}.json: {key}"


def test_every_key_used_in_the_code_exists():
    english = _load_locale("en")
    used = set()
    for path in glob.glob(os.path.join(ROOT, "src", "*.py")):
        with open(path, encoding="utf-8") as f:
            used |= set(re.findall(r"""\btr\(\s*["']([A-Za-z0-9_.]+)["']""", f.read()))
    missing = sorted(k for k in used if k not in english)
    assert not missing, f"keys used but not in en.json: {missing}"


def test_no_dashes_as_punctuation_in_english_strings():
    for key, text in _load_locale("en").items():
        if isinstance(text, str):
            assert "—" not in text and "–" not in text, key
