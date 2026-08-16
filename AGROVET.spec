# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('vista', 'vista'), ('controlador', 'controlador'), ('modelo', 'modelo'), ('data', 'data'), ('AgroVet.sql', '.'), ('README_INSTALACION.txt', '.'), ('config.py', '.'), ('database.py', '.'), ('requirements.txt', '.')],
    hiddenimports=['mysql.connector', 'flask', 'waitress', 'reportlab', 'arabic_reshaper', 'bidi', 'pyphen', 'xhtml2pdf', 'svglib', 'lxml'],
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
    [],
    exclude_binaries=True,
    name='AGROVET',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    upx=True,
    upx_exclude=[],
    name='AGROVET',
)
