# ms-core Sequence

## Inspect State

```bash
git status
git -C ms-core status
git -C ms-core branch --show-current
```

## Commit In ms-core First

```bash
git -C ms-core add <files>
git -C ms-core commit -m "fix: ..."
git -C ms-core push origin <branch>
```

## Update Pointer In Top-Level Repo

```bash
git add ms-core
git add <top-level-files>
git commit -m "fix: bump ms-core for <reason>"
git push origin <branch>
```

## Useful Checks

```bash
git -C ms-core rev-parse --short HEAD
git diff --submodule
PYTHONPATH=ms-core/src pytest tests/ -v --tb=short -x
```

## Common Failure Modes

- `ms-core` commit exists only locally
  - fix by pushing `ms-core` first
- top-level repo points to the wrong submodule SHA
  - fix by restaging `ms-core` after checking out the intended submodule commit
- coordinated fix tested without `PYTHONPATH=ms-core/src`
  - rerun verification with the correct environment
