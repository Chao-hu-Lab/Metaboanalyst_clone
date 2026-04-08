# PyMetaboAnalyst - Development Guide

## Project Structure

- **core/** — pure-function processing modules (normalization, transformation, scaling, etc.)
- **analysis/** — statistical analysis (PCA, PLS-DA, univariate, clustering)
- **visualization/** — matplotlib Figure objects returned by each module
- **gui/** — PyQt6 GUI layer only (no processing logic here)
- **tests/** — pytest test suite

## Development Workflow

### 0. Pre-flight Check (MANDATORY)

Before ANY development work, always run:

```bash
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

```bash
git worktree add .worktrees/<branch-name> -b <type>/<branch-name>
```

Use the `superpowers:using-git-worktrees` skill for guided setup.

### 3. Develop and Test

Run the full test suite before considering work complete:

```bash
pytest tests/ -v --tb=short -x
```

All tests must pass.

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

## Key Commands

```bash
# Run tests
pytest tests/ -v --tb=short -x

# Run tests in the supported CI matrix locally when needed
uv run pytest tests/ -v --tb=short -x

# CI-style full regression
Get-ChildItem tests -Filter "test_*.py" | Sort-Object Name | ForEach-Object { uv run pytest $_.FullName -q }

# Build exe locally (Windows)
pyinstaller packaging/pymetabo.spec --clean --noconfirm

# Build CI-compatible release package locally
pyinstaller packaging/pymetabo_release.spec --clean --noconfirm

# Lint
ruff check . --select=F,E9
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
