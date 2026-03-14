# Phase 2 Visual Validation Checklist

## Automated checks

Run the full test suite:

```bash
python -m pytest tests/ -v
```

Run Phase 2-focused tests only:

```bash
python -m pytest tests/test_theme_manager.py -v
python -m pytest tests/test_gui_layout.py -v
python -m pytest tests/test_plot_toolbar.py -v
```

## Manual verification

1. Launch the app with `python main.py`.
2. Confirm the main toolbar shows a theme selector with `light`, `dark`, and `colorblind`.
3. Switch themes and verify the visualization canvas redraws immediately.
4. Open the Visualization tab and confirm the left parameter dock does not overlap the plot area.
5. Change multiple controls quickly and verify the plot updates once after the debounce delay.
6. Export PNG, SVG, and PDF from the custom toolbar and verify the files open correctly.
7. Use Reset to return controls to their defaults.

## Accessibility check

Use the Okabe-Ito colorblind mode and validate the palette with a simulator:

- https://www.color-blindness.com/coblis-color-blindness-simulator/
