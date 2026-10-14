# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[
        ('build_pyd/gemini_engine.cp312-win_amd64.pyd', '.'),
        ('build_pyd/auth_manager.cp312-win_amd64.pyd', '.')
    ],
    datas=[('app_icon.ico', '.'), ('app_icon.png', '.'), ('update_config.json', '.')],
    hiddenimports=[
        'cryptography',
        'cryptography.fernet',
        'requests',
        'urllib3',
        'PIL',
        'PIL.Image'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gemini_engine', 'auth_manager'],
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
    name='Sonamu_BookEditorOCR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
