#!/bin/bash
# Extract translatable strings into .ts files.

set -e
cd "$(dirname "$0")/.."

find_lupdate() {
  if command -v pyside6-lupdate >/dev/null 2>&1; then
    command -v pyside6-lupdate
    return
  fi

  python - <<'PY'
import glob
import os
import site
import sys

candidates = []
for root in [os.path.dirname(site.getusersitepackages()), *site.getsitepackages()]:
    candidates.extend(glob.glob(os.path.join(root, "Scripts", "pyside6-lupdate*")))
    candidates.extend(glob.glob(os.path.join(root, "bin", "pyside6-lupdate*")))

if candidates:
    print(candidates[0])
else:
    print("pyside6-lupdate")
PY
}

LUPDATE="$(find_lupdate)"
echo "Using lupdate: $LUPDATE"
echo "Extracting translatable strings..."

"$LUPDATE" \
  main.py \
  core/*.py \
  analysis/*.py \
  visualization/*.py \
  gui/*.py \
  gui/widgets/*.py \
  -ts translations/app_en.ts translations/app_zh_TW.ts

echo "Done. Edit .ts files with Qt Linguist, then run scripts/compile_translations.sh"
