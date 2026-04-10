"""
Stable wrapper around scripts/run_from_config.py.

Usage examples:
    python scripts/run_pipeline.py -Config configs/Tissue_knn_rsd050_marker_verify.yaml
    python scripts/run_pipeline.py -Config configs/Tissue_knn_rsd050_marker_verify.yaml -Input "C:/path/to/input.xlsx"
    python scripts/run_pipeline.py -Config configs/Tissue_knn_rsd050_marker_verify.yaml -Input "C:/path/to/input.xlsx" -Suffix "_custom"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def resolve_project_path(path_str: str, repo_root: Path) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stable wrapper for running the pipeline with config/input validation.",
    )
    parser.add_argument("-Config", required=True, help="Path to YAML config file.")
    parser.add_argument("-Input", help="Optional spreadsheet input override.")
    parser.add_argument("-Suffix", help="Optional output suffix override.")
    parser.add_argument(
        "-PythonExe",
        default=sys.executable,
        help="Python executable used to invoke scripts/run_from_config.py.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    runner_path = script_dir / "run_from_config.py"
    if not runner_path.is_file():
        raise FileNotFoundError(f"Runner not found: {runner_path}")

    config_path = resolve_project_path(args.Config, repo_root)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    command = [args.PythonExe, str(runner_path), str(config_path)]

    input_path: Path | None = None
    if args.Input:
        input_path = resolve_project_path(args.Input, repo_root)
        if not input_path.is_file():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        command.extend(["--input", str(input_path)])

    if args.Suffix:
        command.extend(["--suffix", args.Suffix])

    print("Running pipeline...", flush=True)
    print(f"  Config: {config_path}", flush=True)
    if input_path is not None:
        print(f"  Input : {input_path}", flush=True)
    if args.Suffix:
        print(f"  Suffix: {args.Suffix}", flush=True)

    completed = subprocess.run(command, cwd=repo_root, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
