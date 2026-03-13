# Release Commands

## Pre-flight

```bash
git status
git branch --show-current
```

## Version Files

Update:

- `main.py` or the main package `__init__.py` (where `__version__` is defined)

When `pyproject.toml` is added in future: update it as well.

## Default Verification

```bash
pytest tests/ -v --tb=short -x
```

## Version Bump Commit

Example:

```bash
git add main.py
git commit -m "chore(release): bump version to v0.2.0"
```

## Push And Tag

```bash
git push origin main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

## GitHub Release Notes

This repository relies on the tag-triggered workflow:

- `.github/workflows/build.yml`

The workflow:

- builds Windows, macOS, and Linux executables
- uploads artifacts
- creates the GitHub Release with all platform files

## Verification Targets

Check these separately:

1. remote branch updated
2. remote tag exists
3. release workflow started
4. GitHub Release exists
5. release assets exist (Windows zip, macOS DMG, Linux zip)

Never collapse all five into one vague "release done" statement.
