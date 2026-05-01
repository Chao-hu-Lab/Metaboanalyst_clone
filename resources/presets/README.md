# Built-in Presets

This directory contains GUI built-in presets that are safe to expose in the product UI.

- `manifest.yaml` is the whitelist for GUI preset menus.
- Files in `configs/` may still exist for CLI or historical workflows, but they are not treated as GUI built-in presets.
- User-saved local presets belong in the application data directory returned by `get_app_data_dir()/presets`.
- Built-in and seed presets should explicitly list every visible normalization-stage key: `row_norm`, `transform`, `batch_correction`, and `scaling`.
- ComBat support is available. Seed presets should include a `combat` section so users can see the default covariate strategy (`labels`) and advanced options without reading code.
- Built-in presets are intentionally conservative: ComBat is not enabled by default, but the `combat` section is present so GUI and CLI users can turn it on with a clear covariate strategy.
- DNP Step4 marker-aware workflows should use presets/configs that keep `pipeline.impute_method` explicit. `is_Presence_Absence_Marker=True` features are routed to min positive / 5 imputation automatically; non-marker features use the configured method.
