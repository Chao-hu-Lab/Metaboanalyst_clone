# Phase 2 Visual Validation Checklist

## Automated checks

Run the current GUI shell regression group:

```powershell
.\tools\ci\run_pytest_targets.ps1 -GroupNames @("pr-gui-shell")
```

Run Phase 2-focused tests only:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run pytest tests\test_theme_manager.py -q
uv run pytest tests\test_gui_layout_core.py -q
uv run pytest tests\test_plot_toolbar.py -q
```

## Manual verification

1. Launch the app with `uv run python main.py`.
2. Confirm the main toolbar shows a theme selector with `light` and `dark`.
3. Switch themes and verify the visualization canvas redraws immediately.
4. Open the Visualization tab and confirm the left parameter dock does not overlap the plot area.
5. Change multiple controls quickly and verify the plot updates once after the debounce delay.
6. Export PNG, SVG, and PDF from the custom toolbar and verify the files open correctly.
7. Use Reset to return controls to their defaults.

## Accessibility check

Validate that both light and dark themes preserve readable contrast for axis labels,
legends, and toolbar controls:

- https://www.color-blindness.com/coblis-color-blindness-simulator/
