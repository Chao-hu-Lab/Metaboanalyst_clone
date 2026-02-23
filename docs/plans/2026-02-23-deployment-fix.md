# Deployment Fix — PyInstaller 打包修正計畫

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修正所有阻止 PyInstaller 成功打包的問題，讓 Windows 產出可運作的 `PyMetaboAnalyst.exe`（onedir 模式），macOS 產出 `.app` bundle。

**Architecture:** 修正順序為 ① 補齊缺失資源檔 → ② 修正 spec/build 腳本 → ③ 處理缺失依賴的 lazy import → ④ 修正 CI/CD → ⑤ 驗證打包成功。不改動核心邏輯，只修部署層。

**Tech Stack:** PyInstaller 6.19, PySide6 6.10, Python 3.14 (dev) / 3.11 (CI target), Pillow (icon 生成), Inno Setup (Windows installer)

---

## 問題摘要

| # | 問題 | 嚴重度 | 影響 |
|---|---|---|---|
| P1 | `resources/icons/app.ico` 不存在 | 🔴 致命 | PyInstaller 直接 crash |
| P2 | `resources/fonts/` 無字型檔 | 🟡 警告 | 打包成功但 CJK 圖表亂碼 |
| P3 | `qtawesome` 未安裝但 `gui/main_window.py:60` import 它 | 🔴 致命 | exe 啟動即 crash |
| P4 | `fancyimpute`/`pyppca`/`pyopls` 未安裝但被 import | 🟡 警告 | 用到相關功能時 crash |
| P5 | spec 中 `hiddenimports` 不足，缺少 PySide6 plugins | 🟡 警告 | 可能缺少 Qt 平台 plugin |
| P6 | `build.yml` Linux job 引用 `scripts/build.py` 但 icon 不存在導致行為不完整 | 🟡 警告 | CI 構建品質問題 |
| P7 | `build.yml` 無 release job，artifact 不會自動發布 | 🟢 增強 | 手動下載 artifact |
| P8 | Python 3.14 尚未被 PyInstaller 官方支援 | 🟡 風險 | 可能有未知問題 |
| P9 | `pyqtdarktheme` 在 requirements.txt 但實際沒用到（theme.py 是自建的） | 🟢 清理 | 多餘依賴增加打包體積 |

---

## Task 1: 生成 Application Icon 檔案

**Files:**
- Create: `resources/icons/app.ico` (Windows multi-res icon)
- Create: `resources/icons/app.icns` (macOS icon)
- Create: `resources/icons/app_icon.png` (512x512 source PNG)
- Create: `scripts/generate_icon.py` (icon 生成腳本)

**Step 1: 建立 icon 生成腳本**

建立 `scripts/generate_icon.py`，用 Pillow 程式化生成一個簡易的佔位 icon（藍底白字 "MA"）：

```python
"""Generate placeholder application icons using Pillow."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def create_icon(size: int = 512) -> Image.Image:
    """Create a simple placeholder icon: blue circle with 'MA' text."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue circle background
    margin = int(size * 0.05)
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(47, 128, 237),  # #2F80ED accent blue
    )

    # White "MA" text
    font_size = int(size * 0.35)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default(font_size)
    draw.text(
        (size / 2, size / 2),
        "MA",
        fill=(255, 255, 255),
        font=font,
        anchor="mm",
    )
    return img


def main():
    root = Path(__file__).resolve().parent.parent
    icons_dir = root / "resources" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    img = create_icon(512)

    # Save source PNG
    png_path = icons_dir / "app_icon.png"
    img.save(str(png_path))
    print(f"Created: {png_path}")

    # Save Windows ICO (multi-resolution)
    ico_path = icons_dir / "app.ico"
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    resized = [img.resize(s, Image.LANCZOS) for s in sizes]
    resized[0].save(str(ico_path), format="ICO", sizes=sizes, append_images=resized[1:])
    print(f"Created: {ico_path}")

    # Save macOS ICNS
    icns_path = icons_dir / "app.icns"
    img.save(str(icns_path), format="ICNS")
    print(f"Created: {icns_path}")


if __name__ == "__main__":
    main()
```

**Step 2: 執行腳本生成 icon**

Run: `python scripts/generate_icon.py`
Expected: 三個檔案出現在 `resources/icons/`

**Step 3: 驗證 icon 檔案存在且非空**

Run: `ls -la resources/icons/app.ico resources/icons/app.icns resources/icons/app_icon.png`
Expected: 三個檔案皆 >0 bytes

**Step 4: Commit**

```bash
git add scripts/generate_icon.py resources/icons/app.ico resources/icons/app.icns resources/icons/app_icon.png
git commit -m "feat: add generated application icons for Windows/macOS packaging"
```

---

## Task 2: 將缺失的可選依賴改為 Lazy Import

**Files:**
- Modify: `gui/main_window.py:60` (qtawesome import)
- Modify: `core/missing_values.py:16,22` (fancyimpute, pyppca imports)
- Modify: `analysis/oplsda.py:10` (pyopls import)

**問題：** 這些套件是可選功能，但寫在模組頂層 import。如果套件未安裝，整個應用程式連啟動都會失敗。

**Step 1: 修改 `gui/main_window.py` — qtawesome 改為 lazy import**

找到第 60 行的 `import qtawesome as qta`，改為：

```python
try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False
```

在所有使用 `qta.icon(...)` 的地方，加上 guard：

```python
# 原本:
# icon = qta.icon('mdi6.file-upload-outline')
# 改為:
icon = qta.icon('mdi6.file-upload-outline') if _HAS_QTA else None
```

若 `setTabIcon` / `setIcon` 收到 None，需跳過：

```python
if icon is not None:
    self.workflow_tabs.setTabIcon(0, icon)
```

**Step 2: 修改 `core/missing_values.py` — fancyimpute, pyppca 改為 lazy import**

將頂層 import 移到各自的函式內部：

```python
# 移除頂層:
# from fancyimpute import IterativeSVD
# import pyppca

# 在 impute_svd() 函式內部:
def impute_svd(df, rank=2):
    from fancyimpute import IterativeSVD  # lazy import
    ...

# 在 impute_ppca() 函式內部:
def impute_ppca(df, n_components=2):
    import pyppca  # lazy import
    ...
```

**Step 3: 修改 `analysis/oplsda.py` — pyopls 改為 lazy import**

```python
# 移除頂層:
# from pyopls import OPLS

# 在需要的函式內:
def run_oplsda(X, y, ...):
    from pyopls import OPLS  # lazy import
    ...
```

**Step 4: 驗證應用程式在缺少可選套件時仍能啟動**

Run: `python -c "from gui.main_window import MainWindow; print('OK')"`
Expected: 印出 `OK`，無 ImportError

**Step 5: Commit**

```bash
git add gui/main_window.py core/missing_values.py analysis/oplsda.py
git commit -m "fix: convert optional dependencies to lazy imports for packaging"
```

---

## Task 3: 清理 requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: 更新 requirements.txt**

移除實際未使用的 `pyqtdarktheme`（theme.py 是自建 stylesheet，不依賴它）。
將可選依賴與必要依賴分開標註：

```
# === Core (required) ===
numpy
pandas
scipy
scikit-learn
statsmodels
matplotlib
seaborn
PySide6
qnorm
plotly
adjustText
Pillow

# === Optional (enhanced features) ===
# qtawesome        # Icon pack — tab icons fallback to no-icon if missing
# fancyimpute      # SVD imputation method
# pyppca           # PPCA imputation method
# pyopls           # OPLS-DA analysis

# === Removed (not used) ===
# pyqtdarktheme    # Replaced by gui/theme.py custom stylesheet
```

同時建立 `requirements-full.txt` 包含所有套件：

```
-r requirements.txt
qtawesome
fancyimpute
pyppca
pyopls
```

**Step 2: 驗證 pip install 正常**

Run: `pip install -r requirements.txt` (dry-run 檢查語法)
Expected: 無語法錯誤

**Step 3: Commit**

```bash
git add requirements.txt requirements-full.txt
git commit -m "chore: separate optional deps, remove unused pyqtdarktheme"
```

---

## Task 4: 修正 PyInstaller Spec 檔案 (Windows)

**Files:**
- Modify: `packaging/pymetabo.spec`

**Step 1: 修正 spec 檔案**

主要修改：
1. 資源路徑改為安全檢查（icon 不存在時不 crash）
2. 加入更多 `hiddenimports`（PySide6 plugins、scipy submodules）
3. 排除不需要的大型套件（numba、llvmlite 等）減小體積
4. 修正 datas 路徑，只包含存在的檔案

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Windows 版本
用法: pyinstaller packaging/pymetabo.spec --noconfirm --clean
"""

import os
from pathlib import Path

# Resolve paths relative to spec file location
spec_dir = os.path.dirname(os.path.abspath(SPEC))
root_dir = os.path.dirname(spec_dir)

def _data(src_rel, dst):
    """Only include data entry if source exists."""
    src = os.path.join(root_dir, src_rel)
    if os.path.exists(src):
        return (src, dst)
    print(f"WARNING: datas source not found, skipping: {src}")
    return None

_datas_candidates = [
    _data('translations', 'translations'),
    _data('resources/fonts', 'resources/fonts'),
    _data('resources/icons', 'resources/icons'),
]
datas = [d for d in _datas_candidates if d is not None]

# Icon: use if exists, else no icon
icon_path = os.path.join(root_dir, 'resources', 'icons', 'app.ico')
icon_arg = icon_path if os.path.isfile(icon_path) else None

a = Analysis(
    [os.path.join(root_dir, 'main.py')],
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._partition_nodes',
        'sklearn.utils._typedefs',
        'PySide6.QtSvg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numba', 'llvmlite',           # Not needed, saves ~150MB
        'torch', 'tensorflow',          # Never used
        'IPython', 'notebook', 'jupyterlab',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe_kwargs = dict(
    exclude_binaries=True,
    name='PyMetaboAnalyst',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
if icon_arg:
    exe_kwargs['icon'] = icon_arg

exe = EXE(pyz, a.scripts, [], **exe_kwargs)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyMetaboAnalyst',
)
```

**Step 2: 執行打包測試**

Run: `python -m PyInstaller packaging/pymetabo.spec --noconfirm --clean`
Expected: 構建成功，`dist/PyMetaboAnalyst/PyMetaboAnalyst.exe` 存在

**Step 3: 執行 exe 驗證能啟動**

Run: `dist/PyMetaboAnalyst/PyMetaboAnalyst.exe`
Expected: GUI 視窗正常出現（可能無 icon，但不 crash）

**Step 4: Commit**

```bash
git add packaging/pymetabo.spec
git commit -m "fix: robust spec with safe icon/datas handling and reduced bundle size"
```

---

## Task 5: 修正 PyInstaller Spec 檔案 (macOS)

**Files:**
- Modify: `packaging/pymetabo_mac.spec`

**Step 1: 用與 Task 4 相同的邏輯修正 macOS spec**

主要差異：
- Icon 用 `app.icns`
- 加入 `BUNDLE` 段落（已有）
- 排除清單一致

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — macOS 版本
用法: pyinstaller packaging/pymetabo_mac.spec --noconfirm --clean
"""

import os

spec_dir = os.path.dirname(os.path.abspath(SPEC))
root_dir = os.path.dirname(spec_dir)

def _data(src_rel, dst):
    src = os.path.join(root_dir, src_rel)
    if os.path.exists(src):
        return (src, dst)
    print(f"WARNING: datas source not found, skipping: {src}")
    return None

_datas_candidates = [
    _data('translations', 'translations'),
    _data('resources/fonts', 'resources/fonts'),
    _data('resources/icons', 'resources/icons'),
]
datas = [d for d in _datas_candidates if d is not None]

icon_path = os.path.join(root_dir, 'resources', 'icons', 'app.icns')
icon_arg = icon_path if os.path.isfile(icon_path) else None

a = Analysis(
    [os.path.join(root_dir, 'main.py')],
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._partition_nodes',
        'sklearn.utils._typedefs',
        'PySide6.QtSvg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numba', 'llvmlite',
        'torch', 'tensorflow',
        'IPython', 'notebook', 'jupyterlab',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe_kwargs = dict(
    exclude_binaries=True,
    name='PyMetaboAnalyst',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
if icon_arg:
    exe_kwargs['icon'] = icon_arg

exe = EXE(pyz, a.scripts, [], **exe_kwargs)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyMetaboAnalyst',
)

bundle_kwargs = dict(
    name='PyMetaboAnalyst.app',
    bundle_identifier='com.pymetaboanalyst.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '11.0',
        'CFBundleShortVersionString': '1.0.0',
    },
)
if icon_arg:
    bundle_kwargs['icon'] = icon_arg

app = BUNDLE(coll, **bundle_kwargs)
```

**Step 2: Commit** (macOS 構建無法在 Windows 測試)

```bash
git add packaging/pymetabo_mac.spec
git commit -m "fix: robust macOS spec with safe icon handling"
```

---

## Task 6: 修正 `scripts/build.py` 跨平台腳本

**Files:**
- Modify: `scripts/build.py`

**Step 1: 修正 build.py 使用 spec 檔案而非命令行參數**

```python
"""
Cross-platform PyInstaller build helper.
Usage:
    python scripts/build.py          # auto-detect platform
    python scripts/build.py --spec packaging/pymetabo.spec  # explicit
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    system = platform.system()

    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=str, default=None)
    args = parser.parse_args()

    if args.spec:
        spec = Path(args.spec)
    elif system == "Darwin":
        spec = root / "packaging" / "pymetabo_mac.spec"
    else:
        spec = root / "packaging" / "pymetabo.spec"

    if not spec.exists():
        print(f"Error: spec file not found: {spec}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec),
        "--noconfirm", "--clean",
    ]

    print(f"Building for {system} using {spec.name}...")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print("Build complete.")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add scripts/build.py
git commit -m "fix: simplify build.py to use spec files directly"
```

---

## Task 7: 修正 GitHub Actions CI/CD

**Files:**
- Modify: `.github/workflows/build.yml`
- Modify: `.github/workflows/ci.yml`

**Step 1: 修正 `build.yml`**

主要修改：
1. Linux job 改用正確的 spec 檔案路徑
2. 加入 release job 自動發布到 GitHub Releases
3. CI 安裝依賴統一走 `requirements.txt`
4. 鎖定 Python 3.11（打包穩定性）

```yaml
name: Build Release

on:
  push:
    tags: ["v*"]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Generate icons
        run: python scripts/generate_icon.py
      - name: Build with PyInstaller
        run: pyinstaller packaging/pymetabo.spec --noconfirm --clean
      - name: Verify exe exists
        run: test -f dist/PyMetaboAnalyst/PyMetaboAnalyst.exe
        shell: bash
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-Windows
          path: dist/PyMetaboAnalyst/

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Generate icons
        run: python scripts/generate_icon.py
      - name: Build with PyInstaller
        run: pyinstaller packaging/pymetabo_mac.spec --noconfirm --clean
      - name: Create DMG
        run: bash packaging/create_dmg.sh
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-macOS
          path: dist/PyMetaboAnalyst.dmg

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Generate icons
        run: python scripts/generate_icon.py
      - name: Build with PyInstaller
        run: pyinstaller packaging/pymetabo.spec --noconfirm --clean
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-Linux
          path: dist/PyMetaboAnalyst/

  release:
    needs: [build-windows, build-macos, build-linux]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
      - name: Zip Windows build
        run: cd PyMetaboAnalyst-Windows && zip -r ../PyMetaboAnalyst-Windows.zip .
      - name: Zip Linux build
        run: cd PyMetaboAnalyst-Linux && zip -r ../PyMetaboAnalyst-Linux.zip .
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            PyMetaboAnalyst-Windows.zip
            PyMetaboAnalyst-macOS/PyMetaboAnalyst.dmg
            PyMetaboAnalyst-Linux.zip
```

**Step 2: 修正 `ci.yml` 統一依賴安裝**

```yaml
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
```

**Step 3: Commit**

```bash
git add .github/workflows/build.yml .github/workflows/ci.yml
git commit -m "fix: CI uses spec files, add release job, unify deps"
```

---

## Task 8: 修正 Inno Setup 安裝腳本

**Files:**
- Modify: `packaging/inno_setup.iss`

**Step 1: 修正路徑（Windows 反斜線）並加入 ArchitecturesAllowed**

```iss
[Setup]
AppName=PyMetaboAnalyst
AppVersion=1.0.0
AppPublisher=PyMetaboAnalyst
DefaultDirName={autopf}\PyMetaboAnalyst
DefaultGroupName=PyMetaboAnalyst
OutputBaseFilename=PyMetaboAnalyst_Setup_v1.0.0
SetupIconFile=..\resources\icons\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\PyMetaboAnalyst.exe

[Files]
Source: "..\dist\PyMetaboAnalyst\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"
Name: "{autodesktop}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PyMetaboAnalyst.exe"; Description: "Launch PyMetaboAnalyst"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
```

**Step 2: Commit**

```bash
git add packaging/inno_setup.iss
git commit -m "fix: add architecture flags and uninstall config to Inno Setup"
```

---

## Task 9: 本地端打包完整驗證

**Files:** 無修改，純驗證

**Step 1: 生成 icon（如果 Task 1 還沒做）**

Run: `python scripts/generate_icon.py`

**Step 2: 執行 Windows 打包**

Run: `python -m PyInstaller packaging/pymetabo.spec --noconfirm --clean`
Expected: 成功完成，無 ERROR（WARNING 可接受）

**Step 3: 檢查輸出目錄結構**

Run: `ls dist/PyMetaboAnalyst/`
Expected: 包含 `PyMetaboAnalyst.exe`、`translations/`、`resources/` 等

**Step 4: 啟動 exe 驗證**

Run: `./dist/PyMetaboAnalyst/PyMetaboAnalyst.exe`
Expected: GUI 視窗正常出現，可匯入資料、切換分頁

**Step 5: 檢查打包體積**

Run: `du -sh dist/PyMetaboAnalyst/`
Expected: 排除 numba 後應在 200-400MB 範圍

**Step 6: 確認結果後 commit**

```bash
git add -A
git commit -m "chore: verify successful packaging build"
```

---

## 執行順序與依賴關係

```
Task 1 (icon)  ──────────┐
Task 2 (lazy imports) ───┤
Task 3 (requirements) ──┤──→ Task 4 (Win spec) ──→ Task 9 (驗證)
                         │──→ Task 5 (Mac spec)
Task 6 (build.py) ──────┤
Task 7 (CI/CD) ─────────┤
Task 8 (Inno Setup) ────┘
```

Task 1-3 和 6-8 可以並行執行。Task 4-5 依賴 Task 1。Task 9 依賴所有前置。

---

## Python 3.14 注意事項

目前開發環境用 Python 3.14，但 PyInstaller 官方尚未正式支援。兩個策略：

**策略 A（推薦）：** 本地打包也用 3.14，但 CI 鎖 3.11。目前測試 PyInstaller 6.19 在 3.14 上可以運作（已成功跑到 icon 步驟才報錯）。

**策略 B：** 本地用 `py -3.11` 建立 venv 專門打包：
```bash
py -3.11 -m venv .venv-build
.venv-build/Scripts/activate
pip install -r requirements.txt pyinstaller
pyinstaller packaging/pymetabo.spec --noconfirm --clean
```

如果 Task 9 驗證時 3.14 打包出的 exe 有異常行為，再切換到策略 B。

---

## 預估打包體積

| 組件 | 預估大小 |
|---|---|
| PySide6 runtime | ~80MB |
| numpy/scipy/sklearn | ~120MB |
| matplotlib/seaborn/plotly | ~40MB |
| Python runtime | ~30MB |
| 其他 | ~20MB |
| **排除 numba 後總計** | **~290MB** |
| Inno Setup 壓縮後安裝程式 | **~90-120MB** |
