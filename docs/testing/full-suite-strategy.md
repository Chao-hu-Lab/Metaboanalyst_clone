# Full Suite Execution Strategy

This document captures a repository-specific lesson learned:

- For this repository, a single command such as `uv run pytest tests -q`
  is **not** the most reliable default full-suite verification strategy in the
  current environment.

The problem is not test collection. The problem is end-to-end wall-clock time.
When the suite is run as one large process, it can exceed harness time limits
even when the underlying tests are actually passing.

---

## Why this matters

During April 2026 regression verification, the repository test suite:

- collected successfully (`445` tests)
- passed when executed file-by-file
- but timed out when executed as one large `pytest` invocation

This means:

- a single full-suite timeout is not enough evidence to conclude there is a regression
- verification strategy must be adapted to the shape of this repository

---

## Recommended default strategy

### 1. During implementation

Run focused tests first.

Examples:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run pytest tests\test_config_load.py -q
uv run pytest tests\test_paired_analysis.py -q
uv run pytest tests\test_sample_interface.py -q
```

### 2. Before concluding regression status

Run the full suite **file-by-file**, not as one monolithic command.

Recommended PowerShell pattern:

```powershell
$ErrorActionPreference = "Stop"
$files = Get-ChildItem -Path "tests" -Filter "test_*.py" | Sort-Object Name

foreach ($file in $files) {
    Write-Host "=== RUNNING $($file.Name) ==="
    uv run pytest $file.FullName -q
    if ($LASTEXITCODE -ne 0) {
        throw "Test file failed: $($file.Name)"
    }
}
```

This gives three benefits:

- failures are localized to a specific file immediately
- slow files are visible instead of being hidden inside one long run
- a suite-wide timeout no longer obscures whether tests were actually failing

### 3. Treat single-command timeout carefully

If `uv run pytest tests -q` times out:

- do **not** immediately assume the suite is failing
- confirm with file-by-file execution
- report timeout separately from functional failures

---

## Known slow files

The following Phase 7 GUI smoke coverage is known to dominate runtime in the
current Windows harness environment:

- `tests\test_gui_phase7_slow.py`

Observed runtime during the April 2026 verification pass before the split:

- the old `tests\test_gui_layout.py` deep-smoke segment: about 14 minutes

This number may vary by machine, but the general lesson remains:

- this repository has at least one very expensive file
- monolithic full-suite execution hides that fact

---

## Parallel execution note

If faster suite execution is needed, install `pytest-xdist`:

```powershell
uv pip install pytest-xdist
```

Then test whether parallel execution is stable for your environment:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run pytest tests -n auto
```

However:

- GUI-heavy tests may still need special handling even after `xdist`
- parallelism improves throughput, but does not replace focused verification
- parallel execution should be treated as an optimization, not the only source
  of truth

---

## Practical policy

Use this order by default:

1. Focused tests for the files touched in the current change
2. File-by-file full-suite verification when broad regression confidence is needed
3. Optional monolithic or parallel runs when checking for order interactions or benchmarking runtime

This policy is preferred unless the repository test architecture changes enough
to make monolithic full-suite execution consistently reliable.

---

## Current CI policy

The repository CI intentionally does **not** run the same monolithic command on every PR.

Current policy:

1. Python 3.11 keeps the legacy `Full Regression (Python 3.11)` check name for branch protection compatibility
2. Pull requests fan out into domain-oriented smoke shards and then report back through that legacy regression check name via an aggregate job
3. On non-PR events, Python 3.11 still runs broader repository regression shards on the self-hosted Windows runner
4. The known slow GUI smoke cases live in `tests\test_gui_phase7_slow.py` and stay outside the default PR path
5. Embedded `QWebEngineView` coverage runs in its own non-PR smoke lane so PR GUI smoke can stay on the lighter browser-fallback path
6. Python 3.12 runs a targeted compatibility smoke subset on non-PR events only
7. `ruff` is kept as a low-noise guardrail using `--select=F,E9`
8. Shard membership lives in `tools\ci\pytest-target-groups.psd1`, so workflow YAML does not become the only source of truth for repository test topology

Why:

- PR feedback needs to stay within a practical wall-clock budget
- the required regression check name remains stable even though PR and non-PR execution depth now differs
- shard boundaries follow repository domains rather than one giant sequential loop
- the Phase 7 GUI smoke matrix remains valuable, but it should not dominate every PR check
- splitting slow GUI smoke into its own lane makes progress visible and failures easier to interpret
- embedded WebEngine behavior still gets checked, but no longer competes with routine PR feedback on every branch update
- keeping shard membership in a repo-local manifest makes it easier to evolve CI without rewriting job logic
