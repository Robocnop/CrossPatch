"""Version handling, load order and mod list logic."""

import json
import os

import Constants
import ModList
import Util
from conftest import ROOT


def test_version_txt_matches_app_version():
    # Both have to be bumped by hand; the Linux build names its zip from
    # version.txt and the updater compares against APP_VERSION.
    with open(os.path.join(ROOT, "version.txt"), encoding="utf-8") as f:
        assert f.read().strip() == Constants.APP_VERSION


def test_is_newer_version():
    assert Util.is_newer_version("1.2.3", "1.3.0")
    assert Util.is_newer_version("1.2", "1.2.1")
    assert Util.is_newer_version("v1.9", "v1.10")
    assert not Util.is_newer_version("1.3.0", "1.3.0")
    assert not Util.is_newer_version("1.3.0", "v1.3")
    assert not Util.is_newer_version("2.0", "1.9.9")
    assert Util.is_newer_version(None, "0.1")


def test_synchronize_priority_with_disk_keeps_order_and_appends():
    synced = Util.synchronize_priority_with_disk(["B", "Gone", "A"], ["A", "B", "New"])
    assert synced == ["B", "A", "New"]


def test_merge_visible_order_keeps_hidden_mods_in_place():
    full = ["A", "B", "C", "D", "E"]
    # A search shows B and D only, and the user swapped them.
    assert ModList.merge_visible_order(full, ["D", "B"]) == ["A", "D", "C", "B", "E"]


def test_merge_visible_order_with_everything_visible_is_the_tree_order():
    assert ModList.merge_visible_order(["A", "B", "C"], ["C", "A", "B"]) == ["C", "A", "B"]


def test_merge_visible_order_appends_unknown_rows():
    assert ModList.merge_visible_order(["A"], ["A", "New"]) == ["A", "New"]


def test_load_after_moves_mod_behind_the_others():
    assert ModList.load_after(["A", "B", "C", "D"], "A", ["C"]) == ["B", "C", "A", "D"]
    # Already after all of them: untouched.
    assert ModList.load_after(["A", "B", "C"], "C", ["A", "B"]) == ["A", "B", "C"]
    assert ModList.load_after(["A", "B"], "Missing", ["A"]) == ["A", "B"]


def test_matches_filter():
    pak = {"mod_type": "pak"}
    script = {"mod_type": "ue4ss-script"}
    assert ModList.matches_filter("all", pak, False, False, False)
    assert ModList.matches_filter("enabled", pak, True, False, False)
    assert not ModList.matches_filter("enabled", pak, False, False, False)
    assert ModList.matches_filter("disabled", pak, False, False, False)
    assert ModList.matches_filter("updates", pak, False, True, False)
    assert not ModList.matches_filter("conflicts", pak, True, False, False)
    assert ModList.matches_filter("pak", pak, False, False, False)
    assert not ModList.matches_filter("pak", script, False, False, False)
    assert ModList.matches_filter("ue4ss", script, False, False, False)


def test_matches_search():
    info = {"name": "Super Sonic", "version": "2.1", "author": "Someone", "mod_type": "pak"}
    assert ModList.matches_search("", info, "folder")
    assert ModList.matches_search("sonic", info, "folder")
    assert ModList.matches_search("SOMEONE", info, "folder")
    assert ModList.matches_search("fold", info, "folder")
    assert not ModList.matches_search("tails", info, "folder")


def _write_mod(mods_folder, name, files, mod_type="pak"):
    path = os.path.join(mods_folder, name)
    os.makedirs(path, exist_ok=True)
    info = {
        "name": name,
        "mod_type": mod_type,
        "pak_data": {"pak_files": [{"file_path": f"{name}_P.pak", "files": files}]},
    }
    with open(os.path.join(path, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f)


def test_collect_and_group_conflicts(tmp_path):
    mods = str(tmp_path)
    _write_mod(mods, "A", ["Game/Car.uasset", "Game/Only_A.uasset"])
    _write_mod(mods, "B", ["Game/Car.uasset", "Game/Hud.uasset"])
    _write_mod(mods, "C", ["Game/Hud.uasset", "Game/Car.uasset"])
    _write_mod(mods, "Off", ["Game/Car.uasset"])
    profile = {
        "mod_priority": ["A", "B", "C", "Off"],
        "enabled_mods": {"A": True, "B": True, "C": True, "Off": False},
    }

    conflicts = ModList.collect_conflicts(mods, profile)
    assert conflicts == {
        "Game/Car.uasset": ["A", "B", "C"],
        "Game/Hud.uasset": ["B", "C"],
    }
    assert ModList.conflicting_mods(conflicts) == {"A", "B", "C"}

    groups = ModList.group_conflicts(conflicts)
    assert [g["mods"] for g in groups] == [["A", "B", "C"], ["B", "C"]]
    assert groups[0]["files"] == ["Game/Car.uasset"]
