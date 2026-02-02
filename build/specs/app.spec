# -*- mode: python ; coding: utf-8 -*-

# ===============================================================================
# Episode Renamer - PyInstaller Spec
# Build from project root: pyinstaller build/specs/app.spec
# ===============================================================================

import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), '..', '..'))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'src', 'episode_renamer', 'app.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'src')],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        '_tkinter',
        'unittest',
        'pdb',
        'test',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Episode Renamer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Episode Renamer',
)

app = BUNDLE(
    coll,
    name='Episode Renamer.app',
    icon=os.path.join(PROJECT_ROOT, 'resources', 'icons', 'app_icon.icns'),
    bundle_identifier='com.episoderenamer.app',
)
