## Pytest Guidelines

This document captures the recommended pytest baseline for this repository.
It combines official pytest good practices with repository-specific constraints
for Windows, PySide6 GUI tests, and the current sandboxed execution environment.

### Baseline configuration

- Keep all tests under `tests/`
- Use `pytest.ini` as the single shared baseline for team-wide defaults
- Enable:
  - `testpaths = tests`
  - `-ra` for concise failure/skip summary
  - `--strict-markers` so typoed markers fail fast
- Disable `cacheprovider` in this repository environment because pytest cache
  writes have repeatedly failed with Windows `WinError 5` permission errors

Current baseline:

```ini
[pytest]
minversion = 9.0
testpaths = tests
addopts =
    -ra
    --strict-markers
    -p no:cacheprovider
markers =
    gui: PySide6 desktop GUI tests and layout smoke checks.
    slow: Long-running tests that are not ideal for tight edit-run loops.
    integration: Multi-module integration tests that exercise shared config, pipeline, or GUI flows.
```

### Marker policy

- `gui`
  - Any test that requires `QApplication`, `PySide6`, `MainWindow`, or widget interaction
- `slow`
  - Tests that are intentionally expensive or have long wall-clock runtime
  - Current examples: the Phase 7 deep smoke cases inside `tests/test_gui_layout.py`
- `integration`
  - Tests that validate behavior across multiple modules or layers
  - Examples:
    - shared config -> GUI widget state
    - GUI -> pipeline runtime parity
    - preset lifecycle across config + UI

### Fixture policy

- Prefer pytest built-in fixture semantics and naming
- For this repository's Windows sandbox constraints, use repo-local temp
  directories instead of relying on pytest's default temp base path
- Use:
  - `repo_tmp_path_factory`
  - `repo_tmp_path`
- Backward-compatible aliases currently remain:
  - `tmp_path_factory`
  - `tmp_path`
- New tests should prefer the explicit `repo_tmp_path*` fixtures so the
  repository-specific behavior is obvious at the callsite

### GUI testing policy

- All GUI tests should use the shared `qapp` fixture from `tests/conftest.py`
- Layout smoke tests should register failure artifacts with
  `gui_artifact_recorder`
- GUI smoke failures should save widget screenshots only on failure to keep
  normal runs clean
- Keep long GUI geometry suites separate from fast widget-state tests when possible
- In mixed files such as `tests/test_gui_layout.py`, apply `slow` only to the
  deep smoke matrix cases, not to the whole module

### Recommended commands

Fast inner-loop commands:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_app_config.py -q
uv run pytest tests\test_gui_preset_manager.py -q
uv run pytest tests\test_gui_state_binding.py tests\test_gui_config_integration.py -q
```

GUI-only filtering:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -m gui -q
uv run pytest -m "gui and not slow" -q
```

Long smoke verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_gui_layout.py -vv
```

### Audit summary for current repository

#### What is already in a good place

- Tests are already centralized under `tests/`
- Shared fixtures live in `tests/conftest.py`
- GUI tests already reuse one `QApplication` session fixture
- Phase 7 added failure-only GUI screenshot artifacts for smoke regressions
- Shared-config, preset lifecycle, and GUI runtime parity tests are already present

#### Main gaps found during this audit

1. Marker taxonomy was not formalized
   - Result: GUI, integration, and slow tests were not easy to select or exclude
2. Repository-specific temp fixture behavior was hidden behind pytest built-in names
   - Result: `tmp_path` looked standard even though it was custom
3. Pytest cache was unstable in this environment
   - Result: repeated `PytestCacheWarning` noise and transient cache directories
4. Temporary pytest cache probe directories could appear at the repository root
   - Result: noisy `git status` and avoidable workspace clutter

#### Actions taken in this iteration

- Formalized `pytest.ini` baseline
- Registered `gui`, `slow`, and `integration` markers
- Applied markers to the current GUI-focused test modules
- Introduced explicit `repo_tmp_path*` fixture names while preserving backward compatibility
- Disabled `cacheprovider` at the repo baseline
- Ignored transient pytest cache probe directories in `.gitignore`

### Follow-up recommendations

1. Migrate future tests from `tmp_path` to `repo_tmp_path` explicitly
2. Consider splitting `tests/test_gui_layout.py` into:
   - fast layout sanity checks
   - deep smoke matrix
3. Add a CI lane that runs:
   - `-m "not slow"` on every push
   - full GUI smoke on scheduled or release workflows
4. If warning discipline becomes important later, adopt `filterwarnings`
   incrementally rather than switching all warnings to errors at once
