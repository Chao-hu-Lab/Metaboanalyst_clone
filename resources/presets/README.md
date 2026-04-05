# Built-in Presets

This directory contains GUI built-in presets that are safe to expose in the product UI.

- `manifest.yaml` is the whitelist for GUI preset menus.
- Files in `configs/` may still exist for CLI or historical workflows, but they are not treated as GUI built-in presets.
- User-saved local presets belong in the application data directory returned by `get_app_data_dir()/presets`.
