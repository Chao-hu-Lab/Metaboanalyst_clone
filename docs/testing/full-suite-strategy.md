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
uv run pytest tests\test_app_config.py -q
uv run pytest tests\test_paired_analysis.py -q
uv run pytest tests\test_gui_state_binding.py -q
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

The following files are known to dominate full-suite runtime in the current
Windows harness environment:

- `tests\test_gui_layout.py`
- `tests\test_stats_matrix_routing.py`

Observed runtime during the April 2026 verification pass:

- `tests\test_gui_layout.py`: about 14 minutes
- `tests\test_stats_matrix_routing.py`: about 14-15 minutes

These numbers may vary by machine, but the general lesson remains:

- this repository has a few very expensive files
- monolithic full-suite execution hides that fact

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

1. Python 3.11 runs the full suite file-by-file on the self-hosted Windows runner
2. Python 3.12 runs a targeted compatibility smoke subset
3. `ruff` is kept as a low-noise guardrail using `--select=F,E9`

Why:

- Python 3.11 is the main regression signal
- Python 3.12 still provides compatibility coverage without doubling the full-suite wall clock time
- file-by-file execution localizes failures and avoids the false-negative timeout pattern already observed in this repository
