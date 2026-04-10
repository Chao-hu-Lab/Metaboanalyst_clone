"""Guardrails for CI shard membership and pytest marker drift."""

from __future__ import annotations

import ast
from pathlib import Path
import re


MANIFEST_PATH = Path("tools/ci/pytest-target-groups.psd1")
PR_GROUP_NAMES = ("pr-gui-shell", "pr-stats", "pr-runtime")


def _load_group_manifest() -> dict[str, list[str]]:
    group_map: dict[str, list[str]] = {}
    current_group: str | None = None

    for raw_line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = re.match(r'^"([^"]+)"\s*=\s*@\($', line)
        if match:
            current_group = match.group(1)
            group_map[current_group] = []
            continue

        if current_group is None:
            continue

        if line == ")":
            current_group = None
            continue

        target_match = re.match(r'^"([^"]+)"$', line)
        if target_match:
            group_map[current_group].append(target_match.group(1).replace("\\", "/"))

    return group_map


def _pr_smoke_files() -> set[str]:
    files: set[str] = set()

    for path in Path("tests").glob("test_*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if not isinstance(node, ast.Attribute) or node.attr != "pr_smoke":
                continue
            value = node.value
            if not isinstance(value, ast.Attribute) or value.attr != "mark":
                continue
            if isinstance(value.value, ast.Name) and value.value.id == "pytest":
                files.add(path.as_posix())
                break

    return files


def test_ci_group_manifest_targets_exist() -> None:
    group_map = _load_group_manifest()
    assert group_map

    for group_name, targets in group_map.items():
        assert targets, group_name
        for target in targets:
            assert Path(target).exists(), f"{group_name}: missing target {target}"


def test_pr_groups_match_pr_smoke_marker_membership() -> None:
    group_map = _load_group_manifest()
    pr_targets = [
        target
        for group_name in PR_GROUP_NAMES
        for target in group_map[group_name]
    ]

    assert len(pr_targets) == len(set(pr_targets)), "PR shard targets must not overlap"
    assert set(pr_targets) == _pr_smoke_files()
