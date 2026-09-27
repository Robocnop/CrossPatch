"""Mod list logic that needs no widgets: filters, conflict map, load order.

Kept apart from CrossPatch.py so it can be tested without a window.
"""

import os

import Util

FILTER_ALL = "all"
FILTER_ENABLED = "enabled"
FILTER_DISABLED = "disabled"
FILTER_UPDATES = "updates"
FILTER_CONFLICTS = "conflicts"
FILTER_PAK = "pak"
FILTER_UE4SS = "ue4ss"
FILTERS = (FILTER_ALL, FILTER_ENABLED, FILTER_DISABLED, FILTER_UPDATES,
           FILTER_CONFLICTS, FILTER_PAK, FILTER_UE4SS)


def matches_filter(filter_key, info, is_enabled, has_update, has_conflict):
    """True when a mod belongs in the list under the chosen filter."""
    mod_type = (info.get("mod_type") or "pak").lower()
    if filter_key == FILTER_ENABLED:
        return is_enabled
    if filter_key == FILTER_DISABLED:
        return not is_enabled
    if filter_key == FILTER_UPDATES:
        return has_update
    if filter_key == FILTER_CONFLICTS:
        return has_conflict
    if filter_key == FILTER_PAK:
        return mod_type == "pak"
    if filter_key == FILTER_UE4SS:
        return mod_type.startswith("ue4ss")
    return True


def matches_search(search_text, info, folder_name):
    """Case-insensitive match on name, version, author, type or folder."""
    if not search_text:
        return True
    needle = search_text.lower()
    fields = (info.get("name") or folder_name, info.get("version") or "",
              info.get("author") or "", info.get("mod_type") or "pak", folder_name)
    return any(needle in str(field).lower() for field in fields)


def active_game_files(mod_path, info, profile_data):
    """Game paths a pak mod provides, honouring its configuration choices."""
    pak_data = info.get("pak_data") or {}
    active = Util.get_active_pak_files(mod_path, info, profile_data)
    files = set()
    for pak in pak_data.get("pak_files", []):
        pak_path = pak.get("file_path", "")
        if active is not None and not any(pak_path.endswith(p) for p in active):
            continue
        files.update(pak.get("files", []))
    return files


def build_conflict_map(files_by_mod):
    """{game file: [mods providing it, in load order]} for files seen twice.

    files_by_mod is a list of (mod, set of game files) in load order.
    """
    providers = {}
    for mod, files in files_by_mod:
        for game_file in files:
            providers.setdefault(game_file, []).append(mod)
    return {path: mods for path, mods in providers.items() if len(mods) > 1}


def collect_conflicts(mods_folder, profile_data):
    """Conflict map for the enabled pak mods of a profile."""
    enabled = profile_data.get("enabled_mods", {})
    files_by_mod = []
    for mod in profile_data.get("mod_priority", []):
        if not enabled.get(mod, False):
            continue
        mod_path = os.path.join(mods_folder, mod)
        info = Util.read_mod_info(mod_path)
        if (info.get("mod_type") or "pak") != "pak" or not info.get("pak_data"):
            continue
        files_by_mod.append((mod, active_game_files(mod_path, info, profile_data)))
    return build_conflict_map(files_by_mod)


def group_conflicts(conflict_map):
    """Groups files by the exact set of mods fighting over them.

    Returns [{"mods": [...in load order], "files": [...sorted]}], largest
    groups first, which is what a user wants to look at first.
    """
    groups = {}
    for path, mods in conflict_map.items():
        groups.setdefault(tuple(mods), []).append(path)
    result = [{"mods": list(mods), "files": sorted(files)} for mods, files in groups.items()]
    result.sort(key=lambda g: (-len(g["files"]), g["mods"]))
    return result


def conflicting_mods(conflict_map):
    """Every mod involved in at least one conflict."""
    mods = set()
    for providers in conflict_map.values():
        mods.update(providers)
    return mods


def merge_visible_order(full_priority, visible_order):
    """Applies the order of the rows on screen to the full load order.

    With a search or a filter active, the list shows only some mods. Reading
    the load order straight off it used to drop every hidden mod to the end
    of the list on the next save. Here the visible mods are reordered among
    the slots they occupy, and hidden mods keep their place.
    """
    visible = [m for m in visible_order if m in full_priority]
    visible_set = set(visible)
    queue = iter(visible)
    merged = [next(queue) if m in visible_set else m for m in full_priority]
    # Rows the profile did not know yet (a mod that just appeared on disk).
    merged.extend(m for m in visible_order if m not in full_priority)
    return merged


def load_after(priority, mod, others):
    """Moves mod right after the last of `others` in the load order.

    Leaves the list untouched when mod already loads after all of them.
    """
    order = list(priority)
    if mod not in order:
        return order
    positions = [order.index(o) for o in others if o in order and o != mod]
    if not positions or order.index(mod) > max(positions):
        return order
    order.remove(mod)
    last_other = max(order.index(o) for o in others if o in order and o != mod)
    order.insert(last_other + 1, mod)
    return order
