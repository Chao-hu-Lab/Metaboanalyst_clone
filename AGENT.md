# PyMetaboAnalyst - Development Guide

## Project Structure

- **core/** — pure-function processing modules (normalization, transformation, scaling, etc.)
- **analysis/** — statistical analysis (PCA, PLS-DA, univariate, clustering)
- **visualization/** — matplotlib and Plotly rendering helpers used by GUI previews, exports, and reports
- **gui/** — PySide6 GUI layer only (no processing logic here)
- **tests/** — pytest test suite

## Development Workflow

### 0. Pre-flight Check (MANDATORY)

Before ANY development work, always run:

```powershell
git status
```

- Confirm you are on the correct branch (NOT `main` for development)
- Confirm working tree is clean — no uncommitted or untracked changes
- If dirty: commit, stash, or discard before proceeding

### 1. Branch Strategy

| Branch Type | Naming | Purpose |
|-------------|--------|---------|
| `main` | main branch | Merge/PR only, NO direct development |
| `feature/*` | feature branches | New features |
| `fix/*` | fix branches | Bug fixes |
| `chore/*` | chore branches | CI, deps, docs |

### 2. Create Isolated Workspace

Use git worktree for isolation (`.worktrees/` is already in `.gitignore`):

```powershell
git worktree add .worktrees/<branch-name> -b <type>/<branch-name>
```

Use the `superpowers:using-git-worktrees` skill for guided setup.

### 3. Develop and Test

Do not default to a single monolithic `pytest tests/ ...` run in this repo.

This repository contains GUI-heavy and matrix-heavy test slices that can look hung or exceed harness limits when run as one large command, especially on self-hosted Windows CI. Prefer targeted verification first, then run the matching CI-style shard wrapper.

Recommended order:

1. Run the smallest test slice that directly covers the change.
2. Run the matching CI shard with `tools\ci\run_pytest_targets.ps1`.
3. Only use broader file-by-file aggregation when you need wider regression confidence.

Representative commands:

```powershell
# Targeted test during implementation
uv run pytest tests\test_gui_step5_interaction.py -q

# CI-equivalent PR shards
tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-gui-shell")
tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-stats")
tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-runtime")

# Broader file-by-file aggregation when needed
Get-ChildItem tests -Filter "test_*.py" | Sort-Object Name | ForEach-Object { uv run pytest $_.FullName -q }
```

All tests relevant to the current change must pass before considering work complete.

### 4. Finish Branch

Use the `superpowers:finishing-a-development-branch` skill to choose:
1. Merge locally to main
2. Push and create PR
3. Keep branch as-is
4. Discard

### 5. Release

1. Update version in `__init__.py` (when pyproject.toml is added: update both)
2. Commit: `chore: bump version to vX.Y.Z`
3. Push to main
4. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z: description"`
5. Push tag: `git push origin vX.Y.Z`
6. Build workflow auto-creates GitHub Release artifacts for Windows and macOS only

## Submodule Rules (ms-core, when integrated)

When ms-core submodule is added:
1. Make changes inside `ms-core/`
2. Commit and push in ms-core repo FIRST
3. Return to project root, `git add ms-core` to update submodule reference
4. Commit in this repo: `fix: bump ms-core for <reason>`

## Prohibited Actions

- **NO** direct development on `main`
- **NO** force push to `main`
- **NO** merging without passing tests
- **NO** skipping `git status` check before starting work
- **NO** relying on bare `window.close()` as the only teardown step in Qt GUI tests

## Key Commands

```powershell
# Run tests
uv run pytest tests\test_gui_step5_interaction.py -q

# Run CI-equivalent PR shards locally
tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-gui-shell")
tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-stats")
tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-runtime")

# Broader file-by-file regression
Get-ChildItem tests -Filter "test_*.py" | Sort-Object Name | ForEach-Object { uv run pytest $_.FullName -q }

# Preferred stable wrapper (Windows)
scripts\run_pipeline.cmd -Config configs\Tissue_knn_rsd050_marker_verify.yaml -Input "C:\path\to\input.xlsx"

# Run pipeline from YAML
uv run python scripts\run_from_config.py <config.yaml>

# Run pipeline with an explicit input workbook override
uv run python scripts\run_from_config.py <config.yaml> --input "<path-to-input.xlsx>"

# Run pipeline with an input override and output suffix override
uv run python scripts\run_from_config.py <config.yaml> --input "<path-to-input.xlsx>" --suffix "_custom"

# Build exe locally (Windows)
pyinstaller packaging\pymetabo.spec --clean --noconfirm

# Build CI-compatible release package locally
pyinstaller packaging\pymetabo_release.spec --clean --noconfirm

# Lint
ruff check . --select=F,E9
```

## CLI Quick Reference

Use this section first whenever the user asks to "run a config", "use this xlsx with that yaml", or otherwise execute the analysis pipeline from the terminal.

### Natural-Language Execution Contract

When the user writes a request in the form:

- `用 <input.xlsx> 跑 <config.yaml>`
- `幫我用 <input.xlsx> 跑 <config.yaml>`
- `拿這個 xlsx 跑那個 yaml`

interpret it as:

- `input workbook` = the spreadsheet path
- `config` = the yaml path

and execute it directly without re-discovering project structure.

Default command mapping:

```powershell
run.cmd "<input.xlsx>" "<config.yaml>"
```

If the user also asks for a custom output suffix:

```powershell
run.cmd "<input.xlsx>" "<config.yaml>" -Suffix "_custom"
```

Do not spend time re-finding the CLI entry point, config parameter name, or input parameter name for this request pattern unless the wrapper is missing or broken.

### Fastest Human-Style Entry Point

For requests phrased with input first and config second, prefer:

```powershell
run.cmd "<input.xlsx>" "<config.yaml>"
```

- This mirrors the way the user naturally asks for runs.
- Internally it maps to `scripts\run_pipeline.cmd -Config <yaml> -Input <xlsx>`.
- Use this first for one-off execution requests from chat.

### Preferred Stable Command

Prefer this wrapper unless there is a specific reason to call the Python entry point directly:

```powershell
scripts\run_pipeline.cmd -Config <config.yaml> -Input "<input.xlsx>" [-Suffix "_tag"]
```

- This wrapper resolves relative paths from the repo root.
- It validates that the config and input files exist before starting Python.
- It forwards arguments to `scripts\run_from_config.py`.
- The `.cmd` wrapper delegates to `scripts\run_pipeline.py`, which is more reliable than raw shell argument forwarding on Windows.

### Canonical CLI Entry Point

Always use:

```powershell
uv run python scripts\run_from_config.py <config.yaml> [--input "<input.xlsx>"] [--suffix "_tag"]
```

- Script entry point: `scripts\run_from_config.py`
- Required positional argument: `config`
- Optional input override: `--input` or `-i`
- Optional output suffix override: `--suffix` or `-s`

### Parameter Mapping

- If the user gives only a YAML config path:
  - Prefer `scripts\run_pipeline.cmd -Config <config.yaml>`
- If the user gives an XLSX path first and a YAML path second in natural language:
  - Run `run.cmd "<input.xlsx>" "<config.yaml>"`
- If the YAML already has `input.file` filled and the user does not request a different file:
  - Use the YAML as-is
- If the YAML has `input.file: ""` or the user explicitly provides a workbook path:
  - Pass the workbook with `-Input "<input.xlsx>"` on the wrapper, or `--input "<input.xlsx>"` on the Python entry point
- If the user wants a distinct output folder name without editing YAML:
  - Pass `-Suffix "_something"` on the wrapper, or `--suffix "_something"` on the Python entry point

### Standard Operating Procedure

1. Confirm `scripts/run_pipeline.cmd` exists and use it first.
2. Fall back to `scripts/run_from_config.py` only if wrapper debugging is needed.
3. Prefer CLI overrides instead of editing YAML for one-off runs.
4. Treat spreadsheet inputs such as `.xlsx`, `.xlsm`, `.csv`, and `.tsv` as data sources for `--input` when the user provides them explicitly.
5. If the user says "用這個 xlsx 跑這個 yaml", map that to `run.cmd "<input.xlsx>" "<config.yaml>"` without re-discovering the interface.
6. After the run, report:
   - the exact config used
   - the exact input file used
   - the final output directory
   - key high-level metrics from stdout

### Known CLI Contract

From `scripts/run_from_config.py`:

- `config`: required YAML path
- `--input` / `-i`: overrides `cfg["input"]["file"]`
- `--suffix` / `-s`: overrides `cfg["output"]["suffix"]`

Do not re-discover this in later sessions unless the script changes.

### Example

```powershell
run.cmd "C:\Users\user\Desktop\Data_Normalization_project_v2\.worktrees\refactor-step4-pqn-only\output\run_20260331_190146\Step4_Normalized_PQN.xlsx" "configs\Tissue_knn_rsd050_marker_verify.yaml"
```

## Commit Message Convention

Use the `commit-outline` skill to draft messages. Quick reference:

```
<type>(<scope>): <short description>

Scopes: core | analysis | viz | gui | ci | release
Types: feat | fix | refactor | chore | docs | test | build | ci

Examples:
  feat(analysis): add OPLS-DA fallback when pyopls unavailable
  fix(core): correct glog transform lambda parameter
  refactor(viz): simplify boxplot figure creation
  chore(release): bump version to v0.2.0
  test(core): add missing value imputation edge cases
```

## Available Skills

| Skill | When to Use |
|-------|-------------|
| `superpowers:using-git-worktrees` | Before starting any feature work |
| `superpowers:finishing-a-development-branch` | When feature is complete |
| `commit-outline` | Drafting commits, PR summaries, release notes |
| `release-checklist` | Executing a versioned release |
| `submodule-update` | When ms-core is modified (after submodule added) |
| `root-hygiene` | When temp files pollute repository root |
| `run-cmd-contract` | When the user phrases pipeline execution as `用這個 xlsx 跑這個 yaml` or equivalent |

## GUI / CI Guardrails

### Qt GUI Test Teardown

- For PySide / Qt GUI tests, do not stop at bare `window.close()`.
- Prefer the shared cleanup helper in `tests\gui_layout_support.py`.
- The expected teardown shape is:

```python
window.close()
window.deleteLater()
QCoreApplication.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
qapp.processEvents()
```

- If GUI tests get slower the further they progress, first suspect leaked Qt windows, timers, theme callbacks, or log handlers before blaming the runner.

### MainWindow Lifecycle

- When changing `gui\main_window.py`, always review lifecycle symmetry:
  - timers created during setup
  - theme-manager callback registration / unregistration
  - log handler add / remove
  - worker cancellation on close
- If a new resource is created in `__init__` or UI setup, its cleanup path must be explicit.

### Interactive Plot Routing

- For Step 5 score plots, assume the GUI may route to interactive Plotly first and only fall back to Matplotlib when needed.
- When updating tests around PCA / PLS-DA / OPLS-DA / Volcano, verify both:
  - the primary interactive path
  - the fallback static path
- If a test only monkeypatches a legacy Matplotlib helper such as `plot_pca_score`, treat it as suspicious and confirm the real runtime path first.

### CI Refactor Discipline

- When changing CI job names or shard topology, also check branch protection / rulesets for required status-check drift.
- Keep one stable aggregate PR gate name whenever possible. In this repo, the canonical aggregate gate is:
  - `Full Regression (Python 3.11)`
- Treat a long-running `in_progress` PR check as a debugging prompt, not automatic evidence that GitHub Actions itself is broken:
  1. reproduce with the equivalent local shard
  2. identify whether the slowdown is test runtime, repeated setup, or lifecycle leakage
  3. only then change workflow topology if needed
