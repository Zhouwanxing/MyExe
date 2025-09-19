# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['MyExe/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('config/config.yaml', 'config')],
    hiddenimports=['MyExe.gui', 'MyExe.server', 'MyExe.scheduler', 'MyExe.utils.config_loader', 'MyExe.utils.time_utils', 'tkinter', 'fastapi', 'uvicorn', 'yaml'],
    hookspath=[],
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
    a.binaries,
    a.datas,
    [],
    name='MyExeApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
