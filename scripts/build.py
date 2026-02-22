"""
Cross-platform PyInstaller build helper.
Usage:
    python scripts/build.py
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def _add_data_arg(src: str, dst: str) -> str:
    sep = ";" if platform.system() == "Windows" else ":"
    return f"{src}{sep}{dst}"


def main():
    root = Path(__file__).resolve().parent.parent
    app_name = "PyMetaboAnalyst"
    entry = root / "main.py"

    win_icon = root / "resources" / "icons" / "app.ico"
    mac_icon = root / "resources" / "icons" / "app.icns"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={app_name}",
        f"--add-data={_add_data_arg(str(root / 'translations'), 'translations')}",
        f"--add-data={_add_data_arg(str(root / 'resources'), 'resources')}",
        "--hidden-import=sklearn.utils._cython_blas",
        "--hidden-import=sklearn.neighbors._typedefs",
        "--hidden-import=sklearn.neighbors._partition_nodes",
        "--collect-submodules=scipy",
        "--collect-submodules=sklearn",
    ]

    system = platform.system()
    if system == "Windows" and win_icon.exists():
        cmd.append(f"--icon={win_icon}")
    elif system == "Darwin" and mac_icon.exists():
        cmd.append(f"--icon={mac_icon}")

    cmd.append(str(entry))

    print(f"Building {app_name} for {system}...")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print("Build complete.")


if __name__ == "__main__":
    main()
