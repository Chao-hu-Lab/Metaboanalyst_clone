---
name: release-checklist
description: Use when preparing or executing a release for this repository, especially when bumping versions, creating tags, pushing release commits, or verifying that the GitHub Release workflow has produced the expected executables.
---

# Release Checklist

## Overview

Run the repository's release flow in a consistent order. Use this skill when code is already ready to ship and the remaining work is versioning, tagging, pushing, and verifying the release outcome.

## Preconditions

Use this skill only when:

- the requested code changes are already implemented
- relevant verification has passed
- the user wants an actual versioned release, not a draft plan

Stop and ask before proceeding if:

- the working tree contains unrelated changes
- the release version is not specified and cannot be inferred safely

## Version Files

Update the version string in both locations:

1. `main.py` — if `__version__` is defined there, or
2. The relevant `__init__.py` of the main package

When `pyproject.toml` is added in future: update it too.

## Workflow

1. Run pre-flight checks.
   - `git status`
   - `git branch --show-current`
   - confirm the tree is clean enough for a release
2. Run verification before claiming readiness.
   - `pytest tests/ -v --tb=short -x`
3. Update the version string in the version file(s).
4. Re-check the exposed version string locally.
5. Commit the version bump.
   - `chore(release): bump version to vX.Y.Z`
6. Push the branch.
7. Create an annotated tag.
   - `git tag -a vX.Y.Z -m "vX.Y.Z: <short description>"`
8. Push the tag.
   - `git push origin vX.Y.Z`
9. Verify that the tag-triggered GitHub Actions `build.yml` workflow has started.
10. Report the branch commit, tag, and release status separately.

## Release-Specific Rules

- Use annotated tags, not lightweight tags.
- Do not say the release is complete until the tag exists remotely.
- Distinguish:
  - `tag pushed`
  - `workflow triggered`
  - `GitHub Release published`

## Reference Files

- For exact commands and verification points, read:
  - `references/commands.md`

## Output

When finished, report:

- released version
- top-level commit SHA
- tag name
- whether the tag was pushed
- whether the Release workflow or GitHub Release has been verified

If any release step is blocked by auth, network, or GitHub state, state the exact blocking step instead of implying success.
