---
name: submodule-update
description: Use when a task changes ms-core or the top-level repository must point at a new ms-core commit, especially for coordinated fixes spanning both repositories or when the correct submodule commit and push order matters.
---

# Submodule Update

## Overview

Handle coordinated changes between the top-level MetaboAnalyst repository and `ms-core/` without leaving the repositories out of sync. Use this skill whenever `ms-core` code is modified or the submodule pointer needs to advance safely.

## When To Use

Use this skill when:

- files under `ms-core/` are edited
- a top-level change depends on new behavior in `ms-core`
- the user asks to commit or push submodule work
- the correct push order matters

Do not use this skill for top-level-only changes.

## Workflow

1. Inspect both repositories before editing.
   - top-level `git status`
   - `git -C ms-core status`
2. Treat `ms-core` as its own repository.
   - create or use the appropriate branch inside `ms-core`
   - make and verify the `ms-core` change there first
3. Commit the `ms-core` change inside the submodule repository.
4. Push the `ms-core` branch or target branch before touching the top-level pointer commit.
5. Return to the top-level repo.
6. Update the submodule pointer with `git add ms-core`.
7. Stage any top-level files that depend on the new submodule state.
8. Run the relevant top-level verification command with `PYTHONPATH=ms-core/src`.
9. Commit the top-level repo change.
10. Push the top-level repo only after the submodule commit is already reachable remotely.

## Hard Rules

- Never leave a top-level commit pointing at an unpushed `ms-core` commit.
- Never describe a coordinated change as complete if only one repository was pushed.
- If `git` reports safe-directory or auth issues inside `ms-core`, report the exact blocker and stop.
- When the user asks for one commit "for everything", remember that `ms-core` still needs its own commit first.

## Verification

For top-level validation, prefer:

```bash
PYTHONPATH=ms-core/src pytest tests/ -v --tb=short -x
```

For submodule coordination, confirm:

- `git -C ms-core rev-parse --short HEAD`
- top-level `git diff --submodule`
- remote push status for both repositories

## Reference Files

- For exact command order and common failure cases, read:
  - `references/ms-core-sequence.md`

## Output

When reporting status, separate:

- `ms-core` commit SHA and push state
- top-level commit SHA and push state
- whether the top-level repo now points at the intended submodule commit
