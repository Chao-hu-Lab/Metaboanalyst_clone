#!/bin/bash
# Compile .ts files into .qm files.

set -e
cd "$(dirname "$0")/.."

find_lrelease() {
  if command -v pyside6-lrelease >/dev/null 2>&1; then
    command -v pyside6-lrelease
    return
  fi

  python - <<'PY'
import glob
import os
import site

candidates = []
for root in [os.path.dirname(site.getusersitepackages()), *site.getsitepackages()]:
    candidates.extend(glob.glob(os.path.join(root, "Scripts", "pyside6-lrelease*")))
    candidates.extend(glob.glob(os.path.join(root, "bin", "pyside6-lrelease*")))

if candidates:
    print(candidates[0])
else:
    print("pyside6-lrelease")
PY
}

LRELEASE="$(find_lrelease)"
echo "Using lrelease: $LRELEASE"
echo "Compiling translations..."

for ts_file in translations/*.ts; do
  [ -f "$ts_file" ] || continue
  qm_file="${ts_file%.ts}.qm"
  "$LRELEASE" "$ts_file" -qm "$qm_file"
  echo "  $ts_file -> $qm_file"
done

echo "Done."
