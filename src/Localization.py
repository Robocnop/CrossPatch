"""Translations for CrossPatch.

A language is a flat JSON file named after its code. Two folders are scanned:

    assets/locales/<code>.json          shipped with CrossPatch
    <CONFIG_DIR>/locales/<code>.json    added by the user

The user folder is read last, so dropping `fr.json` there overrides the
bundled French without touching the install, and it survives updates. Adding a
brand new language means dropping `<code>.json` in that folder - no rebuild.

File format:

    {
      "_meta": {"name": "Français", "english_name": "French", "code": "fr"},
      "common.ok": "OK",
      "status.idle": "CrossPatch {version}"
    }

`_meta.name` is what the language picker shows, written in that language.
Missing keys fall back to English, then to the key itself, so a partial
translation is perfectly usable.
"""

import json
import os

from Config import CONFIG_DIR

DEFAULT_LANGUAGE = "en"
AUTO = "auto"
LOCALES_DIR_NAME = "locales"

_translations = {}
_catalogue_paths = {}
_active = DEFAULT_LANGUAGE
_initialized = False


def _normalise(code):
    """'fr-FR' and 'fr_fr' both become 'fr_fr'."""
    return (code or "").strip().lower().replace("-", "_")


def user_locales_dir():
    """Folder where users drop their own translations."""
    return os.path.join(CONFIG_DIR, LOCALES_DIR_NAME)


def _locale_dirs():
    """Folders scanned for catalogues, lowest priority first."""
    dirs = []
    try:
        # Imported here on purpose: Util imports this module, so importing it
        # at the top would create a cycle.
        import Util
        assets = Util.find_assets_dir()
        if assets:
            dirs.append(os.path.join(assets, LOCALES_DIR_NAME))
    except Exception as e:
        print(f"Could not locate the assets folder for translations: {e}")
    dirs.append(user_locales_dir())
    return dirs


def discover():
    """Loads every catalogue found on disk. Safe to call again at any time."""
    global _initialized
    _translations.clear()
    _catalogue_paths.clear()

    for directory in _locale_dirs():
        if not os.path.isdir(directory):
            continue
        try:
            entries = sorted(os.listdir(directory))
        except Exception as e:
            print(f"Could not read the translations folder '{directory}': {e}")
            continue

        for entry in entries:
            if not entry.lower().endswith(".json"):
                continue
            path = os.path.join(directory, entry)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("the file must contain a JSON object")
            except Exception as e:
                # One broken file must never take the app down.
                print(f"Ignoring translation file '{path}': {e}")
                continue

            code = _normalise(os.path.splitext(entry)[0])
            _translations[code] = data
            _catalogue_paths[code] = path

    _initialized = True
    return list(_translations)


def ensure_initialized():
    """Loads catalogues and picks the system language if nothing was set yet.

    Lets the very first setup dialogs speak the user's language, before any
    config file exists.
    """
    if not _initialized:
        discover()
        set_language(AUTO)


def available_languages():
    """Maps a language code to the name shown in the picker."""
    if not _initialized:
        discover()
    names = {}
    for code, data in _translations.items():
        meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
        names[code] = meta.get("name") or code
    return dict(sorted(names.items(), key=lambda item: item[1].lower()))


def catalogue_path(code):
    """Where the catalogue for this code was loaded from."""
    return _catalogue_paths.get(_normalise(code))


def _system_language_tags():
    """Language tags reported by the OS, best match first."""
    tags = []

    try:
        from PySide6.QtCore import QLocale
        system = QLocale.system()
        tags.extend(system.uiLanguages())
        tags.append(system.name())
    except Exception:
        pass

    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            # "fr_FR.UTF-8:en_US" -> "fr_FR"
            tags.append(value.split(":")[0].split(".")[0])

    try:
        import locale
        current = locale.getlocale()[0]
        if current:
            tags.append(current)
    except Exception:
        pass

    return [t for t in tags if t]


def detect_system_language():
    """Best installed language for this machine, else English.

    A French Windows reports 'fr-FR'; we try 'fr_fr' first, then 'fr', so a
    generic fr.json is picked up without listing every region.
    """
    if not _initialized:
        discover()

    for tag in _system_language_tags():
        code = _normalise(tag)
        if code in _translations:
            return code
        base = code.split("_")[0]
        if base in _translations:
            return base

    return DEFAULT_LANGUAGE


def set_language(code):
    """Switches language. `auto` (or an empty value) follows the OS."""
    global _active, _initialized
    if not _initialized:
        discover()

    normalised = _normalise(code)
    if not normalised or normalised == AUTO:
        _active = detect_system_language()
    elif normalised in _translations:
        _active = normalised
    else:
        base = normalised.split("_")[0]
        if base in _translations:
            _active = base
        else:
            print(f"Language '{code}' is not installed; falling back to '{DEFAULT_LANGUAGE}'.")
            _active = DEFAULT_LANGUAGE

    _initialized = True
    return _active


def current_language():
    return _active


_qt_translators = []


def install_qt_translations(app=None):
    """Translates Qt's built-in dialog buttons (OK, Cancel, Yes, No, Save).

    Those strings come from Qt, not from our catalogues, so without this they
    stay in English while the rest of the window is translated. Languages Qt
    does not ship simply keep the English buttons.
    """
    try:
        from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
        from PySide6.QtWidgets import QApplication
    except Exception:
        return False

    app = app or QApplication.instance()
    if app is None:
        return False

    for old_translator in _qt_translators:
        app.removeTranslator(old_translator)
    _qt_translators.clear()

    locale = QLocale(_active)
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    installed = False
    for name in ("qtbase", "qt"):
        translator = QTranslator(app)
        if translator.load(locale, name, "_", translations_path):
            app.installTranslator(translator)
            # Keep a reference: Qt drops a translator that gets collected.
            _qt_translators.append(translator)
            installed = True

    if not installed:
        print(f"No Qt translation available for '{_active}'; standard buttons stay in English.")
    return installed


def init(cfg):
    """Called once at startup with the loaded config."""
    discover()
    return set_language(cfg.get("language", AUTO))


def tr(key, **kwargs):
    """Translates `key`, filling in any {placeholders} from kwargs."""
    if not _initialized:
        ensure_initialized()

    text = _translations.get(_active, {}).get(key)
    if text is None:
        text = _translations.get(DEFAULT_LANGUAGE, {}).get(key)
    if text is None:
        # Showing the key beats showing nothing, and it makes the gap obvious.
        return key

    if not kwargs:
        return text

    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        # A community translation with a typo in a placeholder must not crash
        # the app: fall back to English for that one string.
        print(f"Broken placeholder in '{key}' ({_active}): {e}")
        fallback = _translations.get(DEFAULT_LANGUAGE, {}).get(key, key)
        try:
            return fallback.format(**kwargs)
        except Exception:
            return fallback
