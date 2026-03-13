---
name: root-hygiene
description: Keep the repository root clean when working on pytest, temp files, caches, or local artifacts. Use when tests create tmp* folders, .pytest* directories, repo-local caches, or when changing test fixtures or temp-path behavior.
---

# Root Hygiene

## Overview

Use this skill to prevent temporary files, pytest artifacts, and machine-local caches from leaking into the repository root.

This repository's preferred pattern:

- tests use `tmp_path` fixtures provided by pytest (not `TemporaryDirectory(dir=Path.cwd())`)
- ad-hoc cleanup goes through `git clean -fdx --dry-run` first, then manually

If a change touches pytest behavior, temp directories, or cache locations, follow this skill before adding more ignore rules.

## When To Use

Use this skill when:

- `git status` shows `tmp*`, `.pytest*`, `__pycache__`, or `.tmp/` clutter in the root
- tests use `TemporaryDirectory(dir=Path.cwd())` or another path that writes into the repo root
- you are adding or editing tests that need temporary files
- pytest config or temp-path behavior is changing
- you need to clean local artifacts without touching tracked files

Do not use this skill for general cleanup unrelated to test/temp/cache behavior.

## Rules

1. Treat root clutter as a behavior problem first, not an ignore-file problem.
2. Do not introduce `TemporaryDirectory(dir=Path.cwd())` in this repository.
3. For tests, prefer pytest's built-in `tmp_path` fixture — it routes temp files to a system temp directory outside the repo.
4. Use `.gitignore` only as a second line of defense after fixing the write location.

## Workflow

### 1. Inspect before editing

```bash
git status --short
```

Also check:

- `tests/conftest.py` for any temp directory configuration
- `pyproject.toml` (or `pytest.ini`) for `tmp_path_retention_policy` settings

### 2. Fix the source of root clutter

Common fixes:

- replace `TemporaryDirectory(dir=Path.cwd())` with the `tmp_path` fixture
- route analysis output to explicit `analysis_runs/` (already in `.gitignore`)
- avoid re-enabling pytest cache provider (already disabled via `addopts = "-p no:cacheprovider"` if configured)

### 3. Update ignore rules only if needed

Expected ignored local artifacts (already in `.gitignore`):

- `.tmp/`
- `tmp*/`
- `.pytest_cache/`
- `analysis_runs/`
- `analysis_output*/`
- `results/`
- `.worktrees/`

### 4. Verify with focused checks

```bash
pytest tests/ -v --tb=short -x
git status --short
```

Confirm `git status` shows no new untracked clutter after running tests.

## Output Expectations

When reporting the result:

- state which files were causing root clutter
- state which fixture or path policy now owns temp creation
- include the verification commands you ran
- mention any leftover historical temp directories separately from new behavior
