"""
Cross-platform PyInstaller build helper.
Usage:
    python scripts/build.py
    python scripts/build.py --spec packaging/pymetabo.spec
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    system = platform.system()

    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=str, default=None)
    args = parser.parse_args()

    if args.spec:
        spec = Path(args.spec)
    elif system == "Darwin":
        spec = root / "packaging" / "pymetabo_mac.spec"
    else:
        spec = root / "packaging" / "pymetabo.spec"

    if not spec.exists():
        print(f"Error: spec file not found: {spec}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec),
        "--noconfirm", "--clean",
    ]

    print(f"Building for {system} using {spec.name}...")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print("Build complete.")


if __name__ == "__main__":
    main()
