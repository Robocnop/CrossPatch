# -*- mode: python ; coding: utf-8 -*-
# Windows release build. Run from the repository root:
#   python -m PyInstaller packaging\windows\CrossPatch.spec --noconfirm --distpath dist --workpath build\pyi
# Paths are resolved from this file, so the build does not depend on the
# current directory or on where the repository was cloned.
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..', '..'))
SRC = os.path.join(ROOT, 'src')

a = Analysis(
    [os.path.join(SRC, 'Main.py')],
    pathex=[SRC],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[os.path.join(SRC, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CrossPatch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(ROOT, 'assets', 'CrossP.ico')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CrossPatch',
)
