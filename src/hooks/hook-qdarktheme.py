"""PyInstaller hook for qdarktheme.

qdarktheme can bind to PyQt5, PyQt6, PySide2 or PySide6. Left alone,
PyInstaller pulls in every binding it can find and the build ends up with
conflicting copies of Qt. CrossPatch uses PySide6, so the rest are excluded.

The previous version of this hook called hook_api.add_excludes() from a
hook() function. That API was removed in PyInstaller 6, which made the
project impossible to build with any current release. The module-level
declarations below are the supported equivalent.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = ["PyQt5", "PyQt6", "PySide2"]

hiddenimports = collect_submodules("qdarktheme")

# qdarktheme ships stylesheet templates and svg resources next to its code.
datas = collect_data_files("qdarktheme", include_py_files=True)
