# Translations

Place `.ts` and `.qm` files here for PySide6 i18n support.

## File naming convention

- `app_en.ts` / `app_en.qm` — English
- `app_zh_TW.ts` / `app_zh_TW.qm` — Traditional Chinese

## Generate .ts files

```bash
bash scripts/update_translations.sh
```

Or manually:
```bash
pyside6-lupdate main.py gui/*.py gui/widgets/*.py \
    -ts translations/app_en.ts translations/app_zh_TW.ts
```

## Edit translations

Use Qt Linguist or edit .ts XML files directly.

## Compile .qm files

```bash
bash scripts/compile_translations.sh
```

Or manually:
```bash
pyside6-lrelease translations/app_zh_TW.ts -qm translations/app_zh_TW.qm
pyside6-lrelease translations/app_en.ts -qm translations/app_en.qm
```
