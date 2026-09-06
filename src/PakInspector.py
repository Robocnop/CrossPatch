import os
import sys
import json
import subprocess
from typing import Dict, Optional, List

# Where the parser can live, relative to a base directory. The executable has
# no extension on Linux/macOS.
_PARSER_RELATIVE_PATHS = [
    ("tools", "CrossPatchParser", "bin", "Release", "net8.0", "publish", "CrossPatchParser.exe"),
    ("tools", "CrossPatchParser", "bin", "Release", "net8.0", "CrossPatchParser.exe"),
    ("tools", "CrossPatchParser", "bin", "Release", "net7.0", "publish", "CrossPatchParser.exe"),
    ("tools", "CrossPatchParser", "bin", "Release", "net7.0", "CrossPatchParser.exe"),
    ("tools", "CrossPatchParser", "bin", "Release", "net8.0", "publish", "CrossPatchParser"),
    ("tools", "CrossPatchParser", "bin", "Release", "net8.0", "CrossPatchParser"),
    # A packaged build usually ships the parser next to the executable.
    ("tools", "CrossPatchParser.exe"),
    ("tools", "CrossPatchParser"),
    ("CrossPatchParser.exe",),
    ("CrossPatchParser",),
    # Framework-dependent (dll) locations - run via `dotnet <dll>` if found
    ("tools", "CrossPatchParser", "bin", "Release", "net8.0", "publish", "CrossPatchParser.dll"),
    ("tools", "CrossPatchParser", "bin", "Release", "net8.0", "CrossPatchParser.dll"),
    ("tools", "CrossPatchParser", "bin", "Release", "net7.0", "publish", "CrossPatchParser.dll"),
    ("tools", "CrossPatchParser", "bin", "Release", "net7.0", "CrossPatchParser.dll"),
    ("tools", "CrossPatchParser.dll"),
    ("CrossPatchParser.dll",),
]


def _parser_base_dirs() -> List[str]:
    """Directories the parser is searched in.

    Resolving only against __file__ broke packaged builds: PyInstaller and
    Nuitka unpack the sources somewhere temporary, so the bundled parser was
    never found and the app claimed the .NET 8 runtime was missing.
    """
    bases = []

    if getattr(sys, "frozen", False):
        bases.append(os.path.dirname(os.path.abspath(sys.executable)))
    if hasattr(sys, "_MEIPASS"):
        bases.append(sys._MEIPASS)
    try:
        bases.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass
    try:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        bases.append(module_dir)
        bases.append(os.path.dirname(module_dir))
    except NameError:
        pass
    bases.append(os.getcwd())

    seen = set()
    return [b for b in bases if b and not (b in seen or seen.add(b))]


def _subprocess_flags() -> Dict:
    """Keeps a console window from flashing when the GUI runs the parser."""
    if os.name == "nt":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def _possible_parser_paths() -> List[str]:
    paths = []
    for base in _parser_base_dirs():
        for parts in _PARSER_RELATIVE_PATHS:
            paths.append(os.path.join(base, *parts))
    return paths


def run_parser(mod_path: str, name: Optional[str] = None, author: Optional[str] = None,
               version: Optional[str] = None, mount_point: Optional[str] = None,
               parser_path: Optional[str] = None) -> Dict:
    """
    Runs the CrossPatchParser tool to analyze pak files in a mod folder.
    
    Args:
        mod_path: Path to the mod folder containing pak file(s)
        name: Optional mod name
        author: Optional mod author
        version: Optional mod version
        mount_point: Optional mount point override
        parser_path: Optional path to parser executable (to avoid searching multiple times)
        author: Optional mod author
        version: Optional mod version
        mount_point: Optional mount point for pak files

    Returns:
        Dict containing the parsed information
    """
    # Honour a caller-supplied path; only search when none was given.
    # isfile, not exists: 'tools/CrossPatchParser' is also a directory name.
    if not parser_path or not os.path.isfile(parser_path):
        parser_path = next((p for p in _possible_parser_paths() if os.path.isfile(p)), None)

    if not parser_path:
        raise FileNotFoundError(
            "CrossPatchParser executable not found. Please run the build script to publish the tool for your platform. "
            "On Linux/macOS ensure you either publish a self-contained executable or have the .NET runtime installed to run the DLL via 'dotnet'."
        )

    # Determine how to invoke the parser: if it's a .dll, use `dotnet <dll>`;
    # otherwise attempt to execute the found file directly. This covers
    # both framework-dependent and self-contained publishes across OSes.
    if parser_path.lower().endswith('.dll'):
        cmd = ["dotnet", parser_path, "--path", mod_path]
    else:
        cmd = [parser_path, "--path", mod_path]
    if name:
        cmd.extend(["--mod-name", name])
    if author:
        cmd.extend(["--mod-author", author])
    if version:
        cmd.extend(["--mod-version", version])
    if mount_point:
        cmd.extend(["--mount-point", mount_point])

    try:
        # Prevent hangs by adding a timeout (seconds). 30s is a reasonable default
        # for analyzing a small set of pak files; adjust if needed.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30,
                                **_subprocess_flags())
        out = result.stdout.strip()
        if not out:
            # If stdout is empty, include stderr for diagnostics
            raise RuntimeError(f"Parser produced no output. Stderr: {result.stderr.strip()}")
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse tool output: {e}; output starts with: {out[:200]!r}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Parser timed out after 30 seconds")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        raise RuntimeError(f"Parser failed: {stderr}")
def self_contained_parser_available() -> bool:
    """Return True if a self-contained (native) parser executable exists for this platform.

    This checks the same search locations as `run_parser` but only considers
    non-.dll files (executables). On Unix-like systems it also checks the
    executable bit.
    """
    for p in _possible_parser_paths():
        if p.lower().endswith('.dll'):
            continue
        # isfile, not exists: 'tools/CrossPatchParser' is also a directory name.
        if os.path.isfile(p):
            # On POSIX, ensure the file is executable
            try:
                if os.name == 'posix':
                    if os.access(p, os.X_OK):
                        return True
                else:
                    # On Windows, existence is sufficient for .exe
                    return True
            except Exception:
                # If access check fails, fall back to existence
                return True
    return False

def parser_works(timeout: int = 20) -> bool:
    """Checks that the bundled parser actually starts on this machine.

    Existence is not enough. The parser we ship is framework-dependent: it is
    a normal .exe, so it looks available, but it still needs the shared .NET
    runtime and fails at the first pak analysis without it. Asking it to run
    is the only honest answer, and this is only called when dotnet was not
    found anyway.
    """
    parser_path = next((p for p in _possible_parser_paths() if os.path.isfile(p)), None)
    if not parser_path:
        return False

    if parser_path.lower().endswith('.dll'):
        cmd = ["dotnet", parser_path, "--help"]
    else:
        cmd = [parser_path, "--help"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                **_subprocess_flags())
        return result.returncode == 0
    except Exception as e:
        print(f"The pak parser is present but will not run: {e}")
        return False


def generate_mod_pak_manifest(mod_path: str) -> Dict:
    """
    Analyzes all pak files in a mod folder and generates a detailed manifest.

    Args:
        mod_path: Path to the mod folder containing pak file(s)

    Returns:
        Dict containing details about all pak files in the mod
    """
    # Fast path: if the mod already has info.json with pak_data, reuse it
    try:
        info_path = os.path.join(mod_path, "info.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                pak_data = info.get('pak_data')
                if pak_data:
                    return pak_data
            except Exception:
                # Fall back to running parser if info.json malformed
                pass

        result = run_parser(mod_path)
        pak = result.get('pak_data', {})

        # Persist to info.json to speed up future runs
        try:
            if os.path.exists(info_path):
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
            else:
                info = {}
            info['pak_data'] = pak
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
        except Exception:
            # Non-fatal - ignore persistence failures
            pass

        return pak
    except Exception as e:
        print(f"Warning: Pak analysis failed: {e}")
        return {'pak_files': [], 'total_files': 0, 'total_size': 0}