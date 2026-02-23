# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Windows 版本
用法: pyinstaller packaging/pymetabo.spec --noconfirm --clean
"""

import os

spec_dir = os.path.dirname(os.path.abspath(SPEC))
root_dir = os.path.dirname(spec_dir)


def _data(src_rel, dst):
    """Only include data entry if source exists."""
    src = os.path.join(root_dir, src_rel)
    if os.path.exists(src):
        return (src, dst)
    print(f"WARNING: datas source not found, skipping: {src}")
    return None


_datas_candidates = [
    _data('translations', 'translations'),
    _data('resources/fonts', 'resources/fonts'),
    _data('resources/icons', 'resources/icons'),
]
datas = [d for d in _datas_candidates if d is not None]

icon_path = os.path.join(root_dir, 'resources', 'icons', 'app.ico')
icon_arg = icon_path if os.path.isfile(icon_path) else None

a = Analysis(
    [os.path.join(root_dir, 'main.py')],
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._partition_nodes',
        'sklearn.utils._typedefs',
        'PySide6.QtSvg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numba', 'llvmlite',
        'torch', 'tensorflow',
        'IPython', 'notebook', 'jupyterlab',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe_kwargs = dict(
    exclude_binaries=True,
    name='PyMetaboAnalyst',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
if icon_arg:
    exe_kwargs['icon'] = icon_arg

exe = EXE(pyz, a.scripts, [], **exe_kwargs)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyMetaboAnalyst',
)
