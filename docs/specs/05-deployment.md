# Cross-Platform Deployment (Windows + macOS)

> Extracted from CLAUDE.md. Authoritative reference for packaging, signing, and CI/CD.

## Licensing Decision: PySide6 (LGPL) Recommended

**PyQt6 is GPL v3** — closed-source distribution requires a commercial license (~€550/dev/year).
**PySide6 is LGPL** — allows free closed-source distribution.

APIs are ~99.9% identical. **If you plan to distribute as .exe/.app, use PySide6 instead of PyQt6.**

## Additional Dependencies

```bash
pip install pyinstaller pyqtdarktheme qtawesome
```

## Project Structure Extension

```
metaboanalyst_clone/
├── assets/
│   ├── app.ico              # Windows icon (256×256 multi-res)
│   ├── app.icns             # macOS icon (1024×1024)
│   ├── app.png              # Linux / fallback (512×512)
│   └── splash.png           # Splash screen (optional)
├── deploy/
│   ├── pymetaboanalyst.spec  # PyInstaller spec (shared)
│   ├── pymetaboanalyst_mac.spec
│   ├── inno_setup.iss        # Windows Inno Setup script
│   └── Info.plist             # macOS plist overrides
└── .github/
    └── workflows/
        └── build-release.yml  # CI/CD for both platforms
```

## Platform-Specific Handling

```python
import sys, os
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(os.path.abspath('.')) / relative_path

def get_data_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path.home() / '.config'
    path = base / 'PyMetaboAnalyst'
    path.mkdir(parents=True, exist_ok=True)
    return path

def setup_platform():
    if sys.platform == 'win32':
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'com.yourname.pymetaboanalyst'
        )
    elif sys.platform == 'darwin':
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
```

## PyInstaller Configuration

**Always use `--onedir` mode** (not `--onefile`).

**Windows:**
```bash
pyinstaller --noconsole --windowed \
    --name "PyMetaboAnalyst" \
    --icon=assets/app.ico \
    --add-data "translations;translations" \
    --add-data "resources;resources" \
    --add-data "assets;assets" \
    main.py
```

**macOS:**
```bash
pyinstaller --noconsole --windowed \
    --name "PyMetaboAnalyst" \
    --icon=assets/app.icns \
    --add-data "translations:translations" \
    --add-data "resources:resources" \
    --add-data "assets:assets" \
    --osx-bundle-identifier "com.yourname.pymetaboanalyst" \
    main.py
```

## Windows Installer (Inno Setup)

```iss
[Setup]
AppName=PyMetaboAnalyst
AppVersion=1.0.0
DefaultDirName={autopf}\PyMetaboAnalyst
DefaultGroupName=PyMetaboAnalyst
OutputBaseFilename=PyMetaboAnalyst_Setup_1.0.0
SetupIconFile=..\assets\app.ico
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\PyMetaboAnalyst\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"
Name: "{autodesktop}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"

[Run]
Filename: "{app}\PyMetaboAnalyst.exe"; Description: "Launch PyMetaboAnalyst"; Flags: postinstall nowait
```

## macOS Code Signing & Notarization

Required for macOS Sequoia 15+. Needs Apple Developer Program ($99/year).

```bash
# Sign all internal dylibs
find dist/PyMetaboAnalyst.app -name "*.dylib" -o -name "*.so" | while read f; do
    codesign --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
        --options runtime --timestamp "$f"
done

# Sign the app bundle
codesign --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
    --options runtime --deep --timestamp dist/PyMetaboAnalyst.app

# Notarize
ditto -c -k --keepParent dist/PyMetaboAnalyst.app dist/PyMetaboAnalyst.zip
xcrun notarytool submit dist/PyMetaboAnalyst.zip \
    --apple-id "your@email.com" --password "app-specific-password" \
    --team-id "TEAMID" --wait
xcrun stapler staple dist/PyMetaboAnalyst.app

# Create DMG
hdiutil create -volname "PyMetaboAnalyst" \
    -srcfolder dist/PyMetaboAnalyst.app -ov -format UDZO dist/PyMetaboAnalyst.dmg
```

## GitHub Actions CI/CD

Create `.github/workflows/build-release.yml`:

```yaml
name: Build and Release
on:
  push:
    tags: ['v*']

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller deploy/pymetaboanalyst.spec --noconfirm
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
          python-version: '3.12'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller deploy/pymetaboanalyst_mac.spec --noconfirm
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-macOS
          path: dist/PyMetaboAnalyst.dmg

  release:
    needs: [build-windows, build-macos]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            PyMetaboAnalyst-Windows/**
            PyMetaboAnalyst-macOS/**
```

**Required GitHub Secrets:**
- `MACOS_CERT_BASE64` — base64 encoded .p12 certificate
- `MACOS_CERT_PASSWORD` — certificate password
- `APPLE_ID` — Apple developer email
- `APPLE_APP_PASSWORD` — app-specific password
- `APPLE_TEAM_ID` — 10-char team identifier
