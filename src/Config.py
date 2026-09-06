import platform
import os
import json
import sys
import ctypes
import re
if platform.system() == "Windows": import winreg
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

def is_packaged():
    """Checks if the application is running as a packaged executable."""
    return getattr(sys, 'frozen', False) or "__compiled__" in globals()


def get_config_dir():
    """
    Determines the appropriate directory for configuration files.
    If CROSSPATCH_PORTABLE=1 is set, it uses the current working directory.
    Otherwise, it uses platform-specific app data locations.
    """
    if os.environ.get("CROSSPATCH_PORTABLE") == "1":
        return os.getcwd()

    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "CrossPatch")
    else: # Linux and other UNIX-like systems
        return os.path.join(os.path.expanduser("~"), ".config", "CrossPatch")

CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

DEFAULT_MODS_DIR_NAME = "mods"


def ensure_mods_folder(path):
    """Creates the mods folder if it is missing and returns it.

    Returns None when the folder cannot be created (removed external drive,
    bad drive letter, missing permissions...) so callers can react instead of
    silently ending up with an empty mod list.
    """
    if not path:
        return None
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception as e:
        print(f"Could not create mods folder '{path}': {e}")
        return None


def default_mods_folder():
    """Determines the default mods folder path, creating it on disk."""
    if os.environ.get("CROSSPATCH_PORTABLE") == "1":
        path = os.path.join(os.getcwd(), DEFAULT_MODS_DIR_NAME)
        os.makedirs(path, exist_ok=True)
        return path

    # Ensure a QApplication instance exists
    app = QApplication.instance() or QApplication(sys.argv)

    # Pre-create a sensible default so first-time users can simply accept it.
    suggested = os.path.join(CONFIG_DIR, DEFAULT_MODS_DIR_NAME)
    ensure_mods_folder(suggested)

    # Imported here: Localization imports Config, so a module-level import
    # would be circular. This also lets the very first dialog speak the
    # system language, before any config file exists.
    from Localization import ensure_initialized, tr
    ensure_initialized()

    reply = QMessageBox.question(
        None,
        tr("setup.mods.title"),
        tr("setup.mods.body", path=suggested),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )

    if reply == QMessageBox.Yes and os.path.isdir(suggested):
        return suggested

    folder = QFileDialog.getExistingDirectory(
        None,
        tr("setup.mods.pick"),
        suggested,
    )
    if not folder:
        # Cancelling used to abort startup entirely. Fall back to the default
        # instead so the user always ends up with a working install.
        if os.path.isdir(suggested):
            print("No mods folder selected; falling back to the default location.")
            return suggested
        sys.exit("No mods folder selected and the default could not be created. Exiting.")

    return ensure_mods_folder(folder) or folder

def default_game_folder():
    """Tries to auto-detect the game folder, and prompts the user if it fails."""
    default_root = ""
    detected = False
    if platform.system() == "Windows":
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                default_root = _find_game_in_steam_libraries(steam_path)
                detected = bool(default_root)
        except FileNotFoundError:
            print("Steam registry key not found.")
        except OSError as e:
            print(f"Could not read the Steam registry key: {e}")
    elif platform.system() == "Linux":
        # This path is still a guess, but it's a common one.
        linux_path = os.path.join(os.path.expanduser("~"), ".local", "share", "Steam", "steamapps", "common", "SonicRacingCrossWorlds")
        if os.path.isdir(linux_path):
            default_root = linux_path
            detected = True

    if not default_root:
        # Auto-detection failed, prompt the user.
        app = QApplication.instance() or QApplication(sys.argv)
        from Localization import ensure_initialized, tr
        ensure_initialized()
        QMessageBox.information(None, tr("setup.game.title"), tr("setup.game.body"))
        folder = QFileDialog.getExistingDirectory(None, tr("setup.game.pick"))

        if not folder:
            sys.exit("No game folder selected. Exiting.")
        default_root = folder
    return default_root, detected

_original_stdout = sys.stdout
_original_stderr = sys.stderr
_console_streams = None

def show_console():
    if platform.system() != "Windows":
        print("Console toggling is only supported on Windows.")
        return
    global _console_streams
    try:
        if ctypes.windll.kernel32.AllocConsole():
            _console_streams = (
                open("CONOUT$", "w", buffering=1),
                open("CONOUT$", "w", buffering=1)
            )
            sys.stdout = _console_streams[0]
            sys.stderr = _console_streams[1]
            print("Welcome to CrossPatch's Console logs! If you're a regular user there's really no point in having this enabled\nYou should only use this for debugging purposes, serves no other purpose really")
    except Exception as e:
        print(f"Failed to show console: {e}")
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr

def hide_console():
    if platform.system() != "Windows":
        # Nothing to do on non-Windows platforms
        return
    global _console_streams
    try:
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr
        if _console_streams:
            try:
                _console_streams[0].close()
                _console_streams[1].close()
            except:
                pass
            _console_streams = None
        ctypes.windll.kernel32.FreeConsole()
    except Exception as e:
        print(f"Failed to hide console: {e}")

def _find_game_in_steam_libraries(steam_path, app_id="2486820"):
    """Parses Steam's library file to find the game in any library folder."""
    library_folders_vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    app_manifest_file = f"appmanifest_{app_id}.acf"

    # List of all potential library paths, starting with the main one
    library_paths = [steam_path]

    if os.path.exists(library_folders_vdf):
        try:
            with open(library_folders_vdf, "r", encoding="utf-8") as f:
                # This regex finds all "path" values in the VDF file
                found_paths = re.findall(r'"path"\s+"([^"]+)"', f.read())
                for path in found_paths:
                    library_paths.append(path.replace("\\\\", "\\"))
        except Exception as e:
            print(f"Could not parse libraryfolders.vdf: {e}")

    # Now, search for the appmanifest file in each library
    for library_path in library_paths:
        manifest_path = os.path.join(library_path, "steamapps", app_manifest_file)
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Find the "installdir" value
                    match = re.search(r'"installdir"\s+"([^"]+)"', content)
                    if match:
                        game_folder_name = match.group(1)
                        game_path = os.path.join(library_path, "steamapps", "common", game_folder_name)
                        if os.path.isdir(game_path):
                            print(f"Found game at: {game_path}")
                            return game_path
            except Exception as e:
                print(f"Error reading manifest file {manifest_path}: {e}")

    print("Game not found in any Steam library.")
    return "" # Return empty if not found

def _apply_config_defaults(cfg):
    """Fills in keys added by newer CrossPatch versions.

    Configs written by an older release (or hand-edited ones) are missing keys
    that the rest of the app reads with cfg["..."], which used to crash the
    whole window on startup. Returns True when something was added.
    """
    game_root = cfg.get("game_root") or ""
    defaults = {
        "mods_folder": os.path.join(CONFIG_DIR, DEFAULT_MODS_DIR_NAME),
        "game_root": game_root,
        "game_mods_folder": os.path.join(game_root, "UNION", "Content", "Paks", "~mods") if game_root else "",
        "ue4ss_mods_folder": os.path.join(game_root, "UNION", "Binaries", "Win64", "ue4ss", "Mods") if game_root else "",
        "ue4ss_logic_mods_folder": os.path.join(game_root, "UNION", "Content", "Paks", "LogicMods") if game_root else "",
        "enabled_mods": {},
        "show_cmd_logs": False,
        "steam_detected": False,
        "mod_priority": [],
        "window_size": "580x720",
        "language": "auto",
    }

    changed = False
    for key, value in defaults.items():
        if cfg.get(key) is None:
            cfg[key] = value
            changed = True
    return changed


def load_config():
    """Loads the configuration from disk, creating a default one only if it doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            # Basic validation to ensure it's a dictionary
            if isinstance(config_data, dict):
                if _apply_config_defaults(config_data):
                    print("Config was missing some keys; they have been restored.")
                    save_config(config_data)
                # The mods folder may have been deleted or live on a drive that
                # is no longer mounted; recreate it so mods stay visible and
                # downloads have somewhere to land.
                ensure_mods_folder(config_data.get("mods_folder"))
                return config_data
        except json.JSONDecodeError as e:
            # The file is corrupt. Back it up and notify the user.
            print(f"Error loading config.json: {e}")
            corrupt_path = os.path.join(CONFIG_DIR, "config.json.corrupt")
            from Localization import ensure_initialized, tr
            ensure_initialized()
            try:
                app = QApplication.instance() or QApplication(sys.argv)
                os.rename(CONFIG_FILE, corrupt_path)
                QMessageBox.warning(
                    None,
                    tr("setup.corrupt.title"),
                    tr("setup.corrupt.backed_up", path=corrupt_path)
                )
            except Exception as backup_error:
                QMessageBox.critical(
                    None,
                    tr("setup.corrupt.title"),
                    tr("setup.corrupt.failed", error=backup_error)
                )
        except Exception as e:
            print(f"An unexpected error occurred while loading config: {e}")

    # If we reach here, it means no valid config exists. Create a new one.
    print("No valid configuration found. Creating a new one.")
    try:
        default_root, detected = default_game_folder()
        cfg = {
            "mods_folder": default_mods_folder(),
            "game_root": default_root,
            "game_mods_folder": os.path.join(default_root, "UNION", "Content", "Paks", "~mods"),
            "ue4ss_mods_folder": os.path.join(default_root, "UNION", "Binaries", "Win64", "ue4ss", "Mods"),
            "ue4ss_logic_mods_folder": os.path.join(default_root, "UNION", "Content", "Paks", "LogicMods"),
            "enabled_mods": {},
            "show_cmd_logs": False,
            "steam_detected": detected,
            "mod_priority": [],
            "window_size": "580x720"
        }
        save_config(cfg)
        return cfg
    except SystemExit as e:
        # This happens if the user cancels a folder dialog during first-time setup.
        sys.exit(f"Configuration setup cancelled. {e}")

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def register_url_protocol():
    """
    Registers the crosspatch:// URL protocol in the Windows Registry.
    This allows the app to be launched from a web link.
    """
    if platform.system() != "Windows":
        print("URL protocol registration is only supported on Windows.")
        return

    try:
        # The command to execute. It differs between dev and packaged app.
        if is_packaged(): # Packaged app
            command = f'"{sys.executable}" "%1"'
        else: # Development (running with python.exe)
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'Main.py'))
            command = f'"{sys.executable}" "{script_path}" "%1"'

        # Registry path
        key_path = r"Software\Classes\crosspatch"

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, None, winreg.REG_SZ, "URL:CrossPatch Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(key, r"shell\open\command") as command_key:
                winreg.SetValue(command_key, None, winreg.REG_SZ, command)
        print("Successfully registered crosspatch:// URL protocol.")
    except Exception as e:
        print(f"Error: Could not register URL protocol. Please try running as administrator. Details: {e}")
