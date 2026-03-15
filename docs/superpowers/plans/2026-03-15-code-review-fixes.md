# Code Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 code review pain points (prop_cycle conflict, n_jobs hardcode, bilingual labels, zoom double-toggle, hardcoded test exclusion list) in a single commit.

**Architecture:** Each fix is independent and touches exactly one layer. Order: test layer → visualization layer → analysis layer → GUI layer. TDD where practical.

**Tech Stack:** Python 3.10+, PySide6, matplotlib, pytest, seaborn

**Spec:** `docs/superpowers/specs/2026-03-15-code-review-fixes-design.md`

---

## Chunk 1: Test layer + Visualization layer

### Task 1: Fix `test_theme_consistency.py` — Replace hardcoded exclusion set

**Files:**
- Modify: `tests/test_theme_consistency.py:18-22` (delete `_PLOTLY_ONLY_FUNCTIONS` set)
- Modify: `tests/test_theme_consistency.py:54-62` (update `test_theme_parameter_is_actually_used`)

- [ ] **Step 1.1 — Verify current test passes with the set**

  Run:
  ```bash
  pytest tests/test_theme_consistency.py::test_theme_parameter_is_actually_used -v 2>&1 | tail -20
  ```
  Expected: all parametrized cases PASS.

- [ ] **Step 1.2 — Replace `_PLOTLY_ONLY_FUNCTIONS` with `_is_plotly_function()` predicate**

  In `tests/test_theme_consistency.py`, delete lines 18–22 (the `_PLOTLY_ONLY_FUNCTIONS` set) and
  add the helper function in their place:

  ```python
  # DELETE (lines 18-22):
  _PLOTLY_ONLY_FUNCTIONS = {
      "plot_pca_3d",
      "plot_volcano_interactive",
      "plot_roc_interactive",
      "plot_correlation_network_interactive",
  }

  # REPLACE WITH:
  def _is_plotly_function(func) -> bool:
      """Return True if the function builds a Plotly figure rather than matplotlib.

      Detection uses OR-logic on three markers. "import plotly" is the primary
      signal; "go.Figure" and "go.Scatter" are additional fallbacks. A false
      positive would require a non-Plotly function to contain all three strings
      by coincidence — effectively impossible in this codebase.
      """
      source = inspect.getsource(func)
      return any(marker in source for marker in ("import plotly", "go.Figure", "go.Scatter"))
  ```

  Then update `test_theme_parameter_is_actually_used` (the last test in the file):

  ```python
  # BEFORE:
  def test_theme_parameter_is_actually_used(name, func):
      if name in _PLOTLY_ONLY_FUNCTIONS:
          return
      source = inspect.getsource(func)
      assert "apply_publication_style(theme)" in source, (
          f"{name}() accepts 'theme' but does not apply the publication style"
      )

  # AFTER:
  def test_theme_parameter_is_actually_used(name, func):
      """Theme-aware plot helpers should apply the requested theme in their implementation."""
      if _is_plotly_function(func):
          return
      source = inspect.getsource(func)
      assert "apply_publication_style(theme)" in source, (
          f"{name}() accepts 'theme' but does not apply the publication style"
      )
  ```

- [ ] **Step 1.3 — Verify the updated test still passes**

  Run:
  ```bash
  pytest tests/test_theme_consistency.py -v 2>&1 | tail -30
  ```
  Expected: all parametrized cases PASS. The four formerly-hardcoded Plotly functions
  (`plot_pca_3d`, `plot_volcano_interactive`, `plot_roc_interactive`,
  `plot_correlation_network_interactive`) must still be auto-skipped via the new predicate.

---

### Task 2: Fix `visualization/__init__.py` — Remove legacy `prop_cycle`

**Files:**
- Modify: `visualization/__init__.py:7,31-32` (remove seaborn import and two prop_cycle lines)

- [ ] **Step 2.1 — Audit: confirm no plot function relies on prop_cycle for color**

  Run:
  ```bash
  grep -rn "ax\.plot\|ax\.scatter\|ax\.bar\|ax\.fill" visualization/ | grep -v "color=" | grep -v "^Binary\|\.pyc\|#"
  ```
  Expected: zero lines, or only lines in private helper functions that take explicit color
  arguments from callers. If non-zero results appear, manually inspect each to confirm it
  receives color from `get_group_colors()` via the calling function.

- [ ] **Step 2.2 — Delete the prop_cycle lines; conditionally delete the seaborn import**

  Always delete lines 31–32:
  ```python
  COLORBLIND_PALETTE = sns.color_palette("colorblind")                          # line 31 ← DELETE
  matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(color=COLORBLIND_PALETTE)  # line 32 ← DELETE
  ```

  Then check whether the `seaborn` import on line 7 is still needed:
  ```bash
  grep -n "sns\." visualization/__init__.py
  ```
  - If grep returns **zero matches** (lines 31–32 are gone, no other `sns` usage): also delete
    line 7 (`import seaborn as sns`).
  - If `sns.` appears on **any other line**: keep line 7 — seaborn is still used.

  > Note: `seaborn` is used heavily in individual plot modules (e.g. `boxplot.py`,
  > `heatmap.py`) but those are separate files with their own imports. Only `__init__.py`'s
  > own usage matters here.

- [ ] **Step 2.3 — Verify visualization tests still pass**

  Run:
  ```bash
  pytest tests/test_visualization_theme.py tests/test_theme_consistency.py -v 2>&1 | tail -20
  ```
  Expected: all tests PASS.

- [ ] **Step 2.4 — Commit Chunk 1**

  ```bash
  git add tests/test_theme_consistency.py visualization/__init__.py
  git commit -m "fix(viz/test): replace _PLOTLY_ONLY_FUNCTIONS set with dynamic predicate; remove legacy prop_cycle"
  ```

---

## Chunk 2: Analysis layer + GUI layer + Final

### Task 3: Fix `random_forest.py` — Env-var-controlled `n_jobs`

**Files:**
- Modify: `analysis/random_forest.py` (add `_N_JOBS` constant; apply to 3 callsites)
- Modify: `tests/conftest.py` (add `os.environ.setdefault("METABO_N_JOBS", "1")`)

- [ ] **Step 3.1 — Write the failing test**

  Add to `tests/test_core.py` (or a new `tests/test_random_forest_njobs.py` if `test_core.py`
  does not import from `analysis.random_forest`):

  ```python
  def test_random_forest_respects_metabo_n_jobs(monkeypatch):
      """METABO_N_JOBS env var must propagate to RandomForestClassifier n_jobs."""
      import importlib
      import analysis.random_forest as rf_mod

      monkeypatch.setenv("METABO_N_JOBS", "2")
      importlib.reload(rf_mod)           # re-read module-level constant
      assert rf_mod._N_JOBS == 2

      monkeypatch.delenv("METABO_N_JOBS", raising=False)
      importlib.reload(rf_mod)
      assert rf_mod._N_JOBS == -1        # default when env var absent

      # Explicitly restore the test-session state so subsequent tests are not
      # affected. conftest sets METABO_N_JOBS=1 at session start via setdefault,
      # but monkeypatch.delenv removed it — we must reload with the value
      # conftest originally established.
      monkeypatch.setenv("METABO_N_JOBS", "1")
      importlib.reload(rf_mod)
      assert rf_mod._N_JOBS == 1         # back to CI-safe single-process default
  ```

  Run:
  ```bash
  pytest tests/test_random_forest_njobs.py -v 2>&1 | tail -10
  ```
  Expected: FAIL — `AttributeError: module 'analysis.random_forest' has no attribute '_N_JOBS'`

- [ ] **Step 3.2 — Add `_N_JOBS` constant and apply to all three callsites**

  In `analysis/random_forest.py`, near the top (after existing imports), add:
  ```python
  import os

  # Respect METABO_N_JOBS env var for parallelism control.
  # Defaults to -1 (all cores). Set to 1 in restricted environments (CI, PyInstaller).
  _N_JOBS: int = int(os.environ.get("METABO_N_JOBS", "-1"))
  ```

  Then apply `_N_JOBS` to the three callsites:

  ```python
  # Callsite 1 — RandomForestClassifier (around line 102):
  rf = RandomForestClassifier(
      n_estimators=n_trees,
      oob_score=True,
      random_state=random_state,
      n_jobs=_N_JOBS,          # was: n_jobs=1
  )

  # Callsite 2 — cross_val_score (around line 120):
  cv_scores = cross_val_score(rf, X, y, cv=cv, scoring="accuracy", n_jobs=_N_JOBS)

  # Callsite 3 — cross_val_predict (around line 123):
  y_pred = cross_val_predict(rf, X, y, cv=cv, n_jobs=_N_JOBS)
  ```

- [ ] **Step 3.3 — Add env-var default in `tests/conftest.py`**

  In `tests/conftest.py`, after the existing `import os` line (line 5), add:
  ```python
  os.environ.setdefault("METABO_N_JOBS", "1")  # single-process in test environment
  ```

  This must come **before** any test module is imported so the module-level `_N_JOBS` constant
  is set to `1` when the test suite loads `analysis.random_forest`.

- [ ] **Step 3.4 — Run the new test**

  ```bash
  pytest tests/test_random_forest_njobs.py -v 2>&1 | tail -10
  ```
  Expected: PASS.

- [ ] **Step 3.5 — Run the full analysis test suite**

  ```bash
  pytest tests/test_core.py -v 2>&1 | tail -20
  ```
  Expected: all tests PASS (same as before — n_jobs=1 in test environment via conftest).

---

### Task 4: Fix `settings_dialog.py` — Restore Chinese source strings

**Files:**
- Modify: `gui/settings_dialog.py:21,30,32,34-37,46,48,50-51`

No automated test exists for label text, but the strings are verified by grep.

- [ ] **Step 4.1 — Restore 9 `tr()` source strings to Chinese**

  Edit `gui/settings_dialog.py`, replacing each English source string:

  | Line | Current | Replace with |
  |------|---------|-------------|
  | 21 | `self.tr("Settings")` | `self.tr("偏好設定")` |
  | 30 | `self.tr("Appearance")` | `self.tr("外觀")` |
  | 32 | `self.tr("Theme:")` | `self.tr("主題:")` |
  | 34 | `self.tr("Auto")` | `self.tr("自動 (跟隨系統)")` |
  | 35 | `self.tr("Light")` | `self.tr("淺色模式")` |
  | 36 | `self.tr("Dark")` | `self.tr("深色模式")` |
  | 37 | `self.tr("Colorblind-friendly")` | `self.tr("色盲友善")` |
  | 46 | `self.tr("Language")` | `self.tr("語言")` |
  | 48 | `self.tr("Display language:")` | `self.tr("顯示語言:")` |

- [ ] **Step 4.2 — Wrap language combo items in `tr()`**

  Lines 50–51 currently use bare strings without `tr()`:
  ```python
  # BEFORE:
  self.lang_combo.addItem("Traditional Chinese", "zh_TW")
  self.lang_combo.addItem("English", "en")

  # AFTER:
  self.lang_combo.addItem(self.tr("繁體中文"), "zh_TW")
  self.lang_combo.addItem(self.tr("English"), "en")
  ```

  Note: `"繁體中文"` is the native Chinese self-name. `"English"` stays in English (its own
  translation is identical). Both are now translatable via `.ts` files.

- [ ] **Step 4.3 — Verify with grep**

  ```bash
  grep -n "\"Settings\"\|\"Appearance\"\|\"Theme:\"\|\"Light\"\|\"Dark\"\|\"Language\"\|\"Colorblind" gui/settings_dialog.py
  ```
  Expected: zero matches (all English source strings replaced).

  ```bash
  grep -n "addItem" gui/settings_dialog.py
  ```
  Expected: all four `addItem` calls now use `self.tr(...)`.

---

### Task 5: Fix `plot_toolbar.py` — Idempotent zoom toggle

**Files:**
- Modify: `gui/widgets/plot_toolbar.py:28` (`__init__` body, after `self.zoom_mode_enabled = False`)
- Modify: `gui/widgets/plot_toolbar.py:113-119` (`_toggle_zoom` method)
- Test: `tests/test_plot_toolbar.py`

- [ ] **Step 5.1 — Write the failing idempotency test**

  Add to `tests/test_plot_toolbar.py`, after the existing `test_zoom_mode_toggle`.

  > **Pre-check:** Confirm `MplWidget.navigation_toolbar` is a plain instance attribute
  > (not a property): `grep -n "navigation_toolbar" gui/widgets/mpl_canvas.py` — it should
  > appear as `self.navigation_toolbar = NavigationToolbar2QT(...)`. Plain instance attributes
  > can be overwritten directly for testing; properties cannot.

  ```python
  def test_zoom_toggle_is_idempotent(qapp):
      """Calling _toggle_zoom(True) twice must not double-toggle the nav toolbar."""
      from unittest.mock import MagicMock

      toolbar = _make_toolbar(qapp)
      mock_nav = MagicMock()
      # navigation_toolbar is a plain instance attribute on MplWidget — safe to overwrite
      toolbar.mpl_widget.navigation_toolbar = mock_nav

      # First call: should invoke nav.zoom() once
      toolbar._toggle_zoom(True)
      assert mock_nav.zoom.call_count == 1

      # Second call with same state: should NOT invoke nav.zoom() again
      toolbar._toggle_zoom(True)
      assert mock_nav.zoom.call_count == 1   # still 1, not 2

      # Toggle off: should invoke nav.zoom() once more
      toolbar._toggle_zoom(False)
      assert mock_nav.zoom.call_count == 2
  ```

  Run:
  ```bash
  pytest tests/test_plot_toolbar.py::test_zoom_toggle_is_idempotent -v 2>&1 | tail -10
  ```
  Expected: FAIL (current code calls `zoom()` unconditionally every time).

- [ ] **Step 5.2 — Add `_nav_zoom_active` to `__init__`**

  In `gui/widgets/plot_toolbar.py`, in `__init__` after `self.zoom_mode_enabled = False` (line 28):
  ```python
  self.zoom_mode_enabled = False
  self._nav_zoom_active = False      # ← ADD THIS LINE
  ```

- [ ] **Step 5.3 — Replace `_toggle_zoom` body**

  Replace the current `_toggle_zoom` (lines 113–119):
  ```python
  # BEFORE:
  def _toggle_zoom(self, enabled: bool) -> None:
      self.zoom_mode_enabled = enabled
      navigation_toolbar = getattr(self.mpl_widget, "navigation_toolbar", None)
      if navigation_toolbar is not None:
          navigation_toolbar.zoom()
      self.zoom_requested.emit(enabled)

  # AFTER:
  def _toggle_zoom(self, enabled: bool) -> None:
      self.zoom_mode_enabled = enabled                                     # unconditional
      nav = getattr(self.mpl_widget, "navigation_toolbar", None)
      if nav is not None and enabled != self._nav_zoom_active:
          nav.zoom()                                                        # guarded
      self._nav_zoom_active = enabled                                      # unconditional
      self.zoom_requested.emit(enabled)                                    # unconditional
  ```

- [ ] **Step 5.4 — Run the idempotency test**

  ```bash
  pytest tests/test_plot_toolbar.py::test_zoom_toggle_is_idempotent -v 2>&1 | tail -10
  ```
  Expected: PASS.

- [ ] **Step 5.5 — Run the full toolbar test suite to check for regression**

  ```bash
  pytest tests/test_plot_toolbar.py -v 2>&1 | tail -20
  ```
  Expected: all tests PASS, including the existing `test_zoom_mode_toggle` (which checks
  `zoom_mode_enabled` — that assignment is still unconditional so this test is unaffected).

---

### Task 6: Final verification and single commit

- [ ] **Step 6.1 — Run the full relevant test suite**

  ```bash
  pytest tests/test_theme_consistency.py tests/test_visualization_theme.py tests/test_plot_toolbar.py tests/test_random_forest_njobs.py -v 2>&1 | tail -30
  ```
  Expected: all tests PASS.

- [ ] **Step 6.2 — Verify no English source strings remain in settings_dialog**

  ```bash
  grep -c "self\.tr(" gui/settings_dialog.py
  ```
  Expected: count ≥ 11 (9 restored + 2 lang items newly wrapped).

- [ ] **Step 6.3 — Squash Chunk 1 commit and create the single final commit**

  ```bash
  git add analysis/random_forest.py tests/conftest.py tests/test_random_forest_njobs.py \
          gui/settings_dialog.py gui/widgets/plot_toolbar.py tests/test_plot_toolbar.py
  git commit -m "$(cat <<'EOF'
  fix: address phase 1-3 code review pain points

  - visualization/__init__.py: remove legacy prop_cycle that conflicted with theme system
  - analysis/random_forest.py: n_jobs now reads METABO_N_JOBS env var (default -1/all cores)
    applied to RandomForestClassifier, cross_val_score, and cross_val_predict
  - tests/conftest.py: set METABO_N_JOBS=1 for stable single-process test execution
  - gui/settings_dialog.py: restore Chinese source strings per CLAUDE.md bilingual rule;
    wrap language combo items in tr()
  - gui/widgets/plot_toolbar.py: make zoom toggle idempotent via _nav_zoom_active guard
  - tests/test_theme_consistency.py: replace hardcoded _PLOTLY_ONLY_FUNCTIONS set with
    dynamic _is_plotly_function() predicate (auto-detects future Plotly functions)

  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

  > If squashing is needed (Chunk 1 was already committed): use
  > `git rebase -i HEAD~2` to squash the two commits into one before the final message.

- [ ] **Step 6.4 — Final sanity check**

  ```bash
  git log --oneline -3
  git diff HEAD~1 --stat
  ```
  Expected: the latest commit touches exactly the 7 files listed in the spec (6 + optional
  `test_random_forest_njobs.py`), with < 80 lines net change.
