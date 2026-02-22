"""
跨平台工具函式 — 資源路徑、應用程式目錄
"""

import sys
from pathlib import Path


def get_resource_path(relative: str) -> Path:
    """
    取得資源檔案路徑（相容 PyInstaller frozen 模式）

    Parameters
    ----------
    relative : str
        相對於專案根目錄的路徑，如 "resources/fonts/NotoSansCJKtc-Regular.otf"
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包後的路徑
        base = Path(sys._MEIPASS)
    else:
        # 開發模式：專案根目錄
        base = Path(__file__).resolve().parent.parent
    return base / relative


def get_app_data_dir() -> Path:
    """
    取得應用程式資料目錄（設定檔、快取等）

    Windows:  %APPDATA%/PyMetaboAnalyst
    macOS:    ~/Library/Application Support/PyMetaboAnalyst
    Linux:    ~/.config/PyMetaboAnalyst
    """
    import os

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"

    app_dir = base / "PyMetaboAnalyst"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir
