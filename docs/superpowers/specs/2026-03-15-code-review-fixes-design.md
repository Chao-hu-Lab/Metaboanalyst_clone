# Code Review Fix Plan — Phase 1–3 Pain Points

**Date:** 2026-03-15
**Scope:** Single fix commit addressing 5 pain points identified in the Phase 1–3 code review
**Delivery:** One PR — `fix: address phase 1-3 code review pain points`

---

## Background

A code review of the Phase 1–3 visualization theme system upgrade identified 5 pain points spanning
the visualization layer, GUI layer, and test layer. All fixes are small and independent; they are
bundled into a single commit for clarity.

---

## Pain Points & Fixes

### Fix 1 — Remove legacy `prop_cycle` from `visualization/__init__.py`

**File:** `visualization/__init__.py`

**Problem:** Two independent color systems coexist silently:
1. `COLORBLIND_PALETTE` + `matplotlib.rcParams["axes.prop_cycle"]` set at import time
2. `apply_publication_style()` sets `axes.facecolor`, `text.color`, etc. per-theme

Neither system knows about the other. The prop_cycle color order does not match any of the three
theme palettes, so fallback colors (e.g. for `ax.plot()` calls without explicit color) are
inconsistent with the active theme.

**Fix:** Delete the two legacy lines:
```python
# DELETE these two lines
COLORBLIND_PALETTE = sns.color_palette("colorblind")
matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(color=COLORBLIND_PALETTE)
```

If `seaborn` is no longer imported anywhere else in `__init__.py` after this removal, drop the
`import seaborn as sns` line as well. Fallback colors will revert to matplotlib defaults, which is
safer than silent conflicts.

**Risk:** Any plot function that relies on the automatic prop_cycle instead of calling
`get_group_colors()` explicitly will silently change color. Audit with grep:
```
grep -rn "ax\.plot\|ax\.scatter\|ax\.bar" visualization/ | grep -v "color="
```
Expected result: zero or negligible occurrences (all public plot functions already pass explicit
colors via `get_group_colors()`).

---

### Fix 2 — Env-var-controlled `n_jobs` in Random Forest

**Files:** `analysis/random_forest.py`, `tests/conftest.py`

**Problem:** `n_jobs=1` is hardcoded. The original issue was restricted Windows sandbox
environments (CI, PyInstaller sessions) causing named-pipe permission errors with
multiprocessing. All users—including those on multi-core machines—are penalized.

**Fix A — `analysis/random_forest.py`:**
```python
import os

_N_JOBS = int(os.environ.get("METABO_N_JOBS", "-1"))

# Inside RandomForestClassifier call:
n_jobs=_N_JOBS,

# Also pass to cross_val_score and cross_val_predict:
cv_scores = cross_val_score(rf, X, y, cv=cv, scoring="accuracy", n_jobs=_N_JOBS)
y_pred = cross_val_predict(rf, X, y, cv=cv, n_jobs=_N_JOBS)
```

`METABO_N_JOBS` defaults to `-1` (all cores). The module-level constant `_N_JOBS` is read once
at import time to avoid repeated `os.environ` lookups. `_N_JOBS` must be applied to all three
parallel callsites: `RandomForestClassifier`, `cross_val_score`, and `cross_val_predict`.

**Fix B — `tests/conftest.py`:**
```python
import os
os.environ.setdefault("METABO_N_JOBS", "1")
```

`setdefault` is used so that a developer who explicitly sets `METABO_N_JOBS=-1` in their shell
can still override the test default.

**Behaviour table:**

| Environment | `METABO_N_JOBS` set? | Effective n_jobs |
|---|---|---|
| Normal user (GUI) | No | -1 (all cores) |
| CI pipeline | No (conftest sets 1) | 1 |
| Developer override | Yes (any value) | that value |
| PyInstaller bundle | Recommend setting to 1 in launch script | 1 |

---

### Fix 3 — Restore bilingual source strings in `settings_dialog.py`

**File:** `gui/settings_dialog.py`

**Problem:** Phase 2 changed source strings from Chinese to English, violating the CLAUDE.md rule:
> "GUI labels: bilingual — wrap in `self.tr()` for i18n"

The rule treats Chinese as the default surface language; English translations are provided via
`.ts` translation files.

**Fix:** Restore the following source strings (keep `tr()` wrapping intact):

| Current (English) | Restored (Chinese) |
|---|---|
| `self.tr("Settings")` | `self.tr("偏好設定")` |
| `self.tr("Appearance")` | `self.tr("外觀")` |
| `self.tr("Theme:")` | `self.tr("主題:")` |
| `self.tr("Auto")` | `self.tr("自動 (跟隨系統)")` |
| `self.tr("Light")` | `self.tr("淺色模式")` |
| `self.tr("Dark")` | `self.tr("深色模式")` |
| `self.tr("Colorblind-friendly")` | `self.tr("色盲友善")` |
| `self.tr("Language")` | `self.tr("語言")` |
| `self.tr("Display language:")` | `self.tr("顯示語言:")` |

**Language selector items (intentionally NOT wrapped in `tr()`):**
`addItem("Traditional Chinese", "zh_TW")` and `addItem("English", "en")` show language names
in their own script — this is standard UX for language selectors (users must be able to find
their language even before the app is set to the right locale). These two items should be
wrapped in `tr()` but their source strings should remain in native form:
```python
self.lang_combo.addItem(self.tr("繁體中文"), "zh_TW")
self.lang_combo.addItem(self.tr("English"), "en")
```
`"繁體中文"` is the Chinese self-name; `"English"` stays as-is since its English translation
is identical. This adds `tr()` coverage without changing display text.

No other logic changes. Combo box data values and i18n infrastructure are unchanged.

---

### Fix 4 — Idempotent zoom toggle in `PlotToolbar`

**File:** `gui/widgets/plot_toolbar.py`

**Problem:** `_toggle_zoom` unconditionally calls `navigation_toolbar.zoom()`, which is itself a
toggle. If the button state and the toolbar state diverge (e.g. user clicks rapidly), the two
toggles fall out of sync.

**Fix:** The current code calls `navigation_toolbar.zoom()` unconditionally on every button toggle,
which causes double-toggling if the button is rapidly clicked. Track the nav toolbar's zoom state
with a private instance variable and guard only the `nav.zoom()` call:

```python
# In __init__, add one line:
self._nav_zoom_active = False

def _toggle_zoom(self, enabled: bool) -> None:
    self.zoom_mode_enabled = enabled          # UNCONDITIONAL — update public state
    nav = getattr(self.mpl_widget, "navigation_toolbar", None)

    if nav is not None and enabled != self._nav_zoom_active:
        nav.zoom()                            # Only called when state must change

    self._nav_zoom_active = enabled           # UNCONDITIONAL — always sync tracked state
    self.zoom_requested.emit(enabled)         # UNCONDITIONAL — emit regardless
```

**Critical implementation notes:**
- `self.zoom_mode_enabled = enabled`, `self._nav_zoom_active = enabled`, and
  `zoom_requested.emit(enabled)` are all **unconditional** — they execute on every call.
- Only `nav.zoom()` is inside the guard. Moving any of the three unconditional lines inside the
  guard would break `test_zoom_mode_toggle` or cause state divergence.
- `_nav_zoom_active` is assigned **outside** the guard so the tracked state always reflects the
  desired state, even if `nav.zoom()` was skipped. This guarantees true idempotency: calling
  `_toggle_zoom(True)` twice in a row has no side effect the second time.

---

### Fix 5 — Dynamic Plotly-function detection in `test_theme_consistency.py`

**File:** `tests/test_theme_consistency.py`

**Problem:** `_PLOTLY_ONLY_FUNCTIONS` is a hardcoded set of strings. New interactive chart
functions added in the future require a manual update to this set or the
`test_theme_parameter_is_actually_used` test will produce a false failure.

**Fix:** Replace the static set with a runtime predicate that inspects the function source:

```python
# DELETE this set:
_PLOTLY_ONLY_FUNCTIONS = {
    "plot_pca_3d",
    "plot_volcano_interactive",
    "plot_roc_interactive",
    "plot_correlation_network_interactive",
}

# ADD this helper:
def _is_plotly_function(func) -> bool:
    """Return True if the function builds a Plotly figure (not matplotlib)."""
    source = inspect.getsource(func)
    return any(marker in source for marker in ("import plotly", "go.Figure", "go.Scatter"))

# UPDATE the test:
def test_theme_parameter_is_actually_used(name, func):
    if _is_plotly_function(func):
        return
    source = inspect.getsource(func)
    assert "apply_publication_style(theme)" in source, (
        f"{name}() accepts 'theme' but does not apply the publication style"
    )
```

Any future `plot_xxx_interactive` function that contains `import plotly` or `go.Figure` is
automatically excluded without touching the test file.

---

## Delivery

### Single commit message
```
fix: address phase 1-3 code review pain points

- visualization/__init__.py: remove legacy prop_cycle (conflicts with theme system)
- analysis/random_forest.py: read n_jobs from METABO_N_JOBS env var (default -1, applied to RF + CV calls)
- tests/conftest.py: set METABO_N_JOBS=1 for stable test isolation
- gui/settings_dialog.py: restore Chinese source strings per CLAUDE.md
- gui/widgets/plot_toolbar.py: make zoom toggle idempotent (compare nav.mode state)
- tests/test_theme_consistency.py: replace hardcoded _PLOTLY_ONLY_FUNCTIONS with
  dynamic _is_plotly_function() predicate
```

### Files changed (6 files, estimated < 50 lines net)

| File | Change type | Lines (est.) |
|---|---|---|
| `visualization/__init__.py` | Delete 2 lines (+ possibly 1 import) | −3 |
| `analysis/random_forest.py` | Replace literal with env-var read | +3 / −1 |
| `tests/conftest.py` | Add env var default | +2 |
| `gui/settings_dialog.py` | Restore 9 source strings + wrap 2 lang items in tr() | +11 / −11 |
| `gui/widgets/plot_toolbar.py` | 3-line conditional replace 1-line call | +4 / −1 |
| `tests/test_theme_consistency.py` | Replace set + update test | +7 / −6 |

### Test strategy
- Run `pytest tests/test_theme_consistency.py tests/test_plot_toolbar.py tests/test_visualization_theme.py -v` after changes
- Grep audit for `ax.plot\|ax.scatter\|ax.bar` without `color=` in `visualization/` to confirm prop_cycle removal is safe
- Manually verify Settings dialog shows Chinese labels on app launch

---

## Out of Scope

- Fixing the remaining `gui/main_window.py` / `gui/visual_tab.py` English labels (separate i18n Phase 4 task)
- Adding PyInstaller launch script to set `METABO_N_JOBS=1` (deployment concern, Phase 5)
- Replacing the source-string matching in `test_theme_parameter_is_actually_used` with a more
  principled contract (e.g. a decorator or protocol) — the current fix is sufficient
