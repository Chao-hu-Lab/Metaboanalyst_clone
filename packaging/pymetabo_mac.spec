# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — macOS 版本
用法: pyinstaller packaging/pymetabo_mac.spec --noconfirm --clean
注意: macOS 不上架 App Store，使用者需自行處理隱私權驗證
"""

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../translations/*.qm', 'translations'),
        ('../resources/fonts', 'resources/fonts'),
        ('../resources/icons', 'resources/icons'),
    ],
    hiddenimports=[
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._partition_nodes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PyMetaboAnalyst',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='../resources/icons/app.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyMetaboAnalyst',
)

app = BUNDLE(
    coll,
    name='PyMetaboAnalyst.app',
    icon='../resources/icons/app.icns',
    bundle_identifier='com.pymetaboanalyst.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '11.0',
        'CFBundleShortVersionString': '1.0.0',
    },
)
