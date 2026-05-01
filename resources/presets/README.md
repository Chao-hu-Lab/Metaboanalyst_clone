# Built-in Presets

This directory contains GUI built-in presets that are safe to expose in the product UI.

- `manifest.yaml` is the whitelist for GUI preset menus.
- Files in `configs/` may still exist for CLI or historical workflows, but they are not treated as GUI built-in presets.
- User-saved local presets belong in the application data directory returned by `get_app_data_dir()/presets`.
- Built-in and seed presets should explicitly list every visible normalization-stage key: `row_norm`, `transform`, `batch_correction`, and `scaling`.
- When ComBat support is available, seed presets should also include a `combat` section so users can see the default covariate strategy (`labels`) and advanced options without reading code.
