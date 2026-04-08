# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec used by the shared GitHub Actions desktop build workflow.

Outputs:
- Windows: dist/PyMetaboAnalyst.exe
- macOS:   dist/PyMetaboAnalyst.app
"""

import os
import sys

spec_dir = os.path.dirname(os.path.abspath(SPEC))
root_dir = os.path.dirname(spec_dir)


def _data(src_rel, dst):
    src = os.path.join(root_dir, src_rel)
    if os.path.exists(src):
        return (src, dst)
    print(f"WARNING: datas source not found, skipping: {src}")
    return None


_datas_candidates = [
    _data("translations", "translations"),
    _data("resources/fonts", "resources/fonts"),
    _data("resources/icons", "resources/icons"),
]
datas = [item for item in _datas_candidates if item is not None]

icon_name = "app.icns" if sys.platform == "darwin" else "app.ico"
icon_path = os.path.join(root_dir, "resources", "icons", icon_name)
icon_arg = icon_path if os.path.isfile(icon_path) else None

a = Analysis(
    [os.path.join(root_dir, "main.py")],
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "sklearn.utils._cython_blas",
        "sklearn.neighbors._typedefs",
        "sklearn.neighbors._partition_nodes",
        "sklearn.utils._typedefs",
        "PySide6.QtSvg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "numba",
        "llvmlite",
        "torch",
        "tensorflow",
        "IPython",
        "notebook",
        "jupyterlab",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe_kwargs = dict(
    name="PyMetaboAnalyst",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
if icon_arg:
    exe_kwargs["icon"] = icon_arg

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    **exe_kwargs,
)

if sys.platform == "darwin":
    bundle_kwargs = dict(
        name="PyMetaboAnalyst.app",
        bundle_identifier="com.pymetaboanalyst.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion": "11.0",
            "CFBundleShortVersionString": "1.0.0",
        },
    )
    if icon_arg:
        bundle_kwargs["icon"] = icon_arg
    app = BUNDLE(exe, **bundle_kwargs)
