# Cross-Platform Deployment (Windows + macOS)

> Current authoritative reference for packaging, release artifacts, and CI/CD.

## Supported Targets

- Supported desktop release targets: Windows and macOS
- Linux is not a maintained release target for this repository
- CI test matrix: Python 3.11 / 3.12
- Desktop build workflow currently packages artifacts with Python 3.11 through the shared workflow

## Packaging Files

```text
metaboanalyst_clone/
├── packaging/
│   ├── pymetabo.spec           # Local Windows onedir build
│   ├── pymetabo_mac.spec       # Local macOS app bundle build
│   ├── pymetabo_release.spec   # CI/release spec for shared workflow
│   ├── inno_setup.iss          # Windows installer script
│   └── create_dmg.sh           # Optional local macOS DMG helper
├── resources/
│   ├── fonts/
│   └── icons/
│       ├── app.ico
│       └── app.icns
└── .github/workflows/
    ├── ci.yml
    └── build.yml
```

## Resource Resolution

Runtime resource lookup is implemented in `core/utils.py` via `get_resource_path()`.

- Frozen app: resolves from `sys._MEIPASS`
- Dev mode: resolves from the repository root

This is why PyInstaller specs must include:

- `translations/`
- `resources/fonts/`
- `resources/icons/`

## Local Build Commands

### Windows local build

```powershell
pyinstaller packaging\pymetabo.spec --clean --noconfirm
```

Output:

- `dist\PyMetaboAnalyst\PyMetaboAnalyst.exe`

Use this path with `packaging\inno_setup.iss` if you want a Windows installer.

### macOS local build

```bash
pyinstaller packaging/pymetabo_mac.spec --clean --noconfirm
```

Output:

- `dist/PyMetaboAnalyst.app`

Optional local DMG creation:

```bash
bash packaging/create_dmg.sh
```

## CI / Release Build

The repository no longer keeps custom per-platform build logic in caller workflows.
Instead, it delegates to pinned reusable workflows from `Chao-hu-Lab/shared-workflows`.

### CI workflow

File: `.github/workflows/ci.yml`

- Calls shared `python-ci.yml`
- Runs tests on the self-hosted runner label set `[self-hosted, Windows, X64]`
- Uses Python `3.11` and `3.12`
- Keeps a separate `ruff` lint job on `ubuntu-latest`

### Build workflow

File: `.github/workflows/build.yml`

- Calls shared `python-build.yml`
- Triggered by tags matching `v*.*.*`
- Supports manual `workflow_dispatch`
- Publishes Windows and macOS artifacts only
- Uses `packaging/pymetabo_release.spec`

Current release artifact contract:

- Windows artifact contains `PyMetaboAnalyst.exe`
- macOS artifact contains `PyMetaboAnalyst.app`
- Shared workflow packages both outputs as zip artifacts / release assets

## Why CI Uses a Separate Spec

`packaging/pymetabo_release.spec` exists to match the output contract expected by the shared build workflow:

- Windows: `dist/PyMetaboAnalyst.exe`
- macOS: `dist/PyMetaboAnalyst.app`

This is intentionally separate from local packaging specs:

- local Windows installer flow still uses `packaging/pymetabo.spec`
- local macOS DMG flow still uses `packaging/pymetabo_mac.spec` and `packaging/create_dmg.sh`

That split keeps CI/CD deterministic without forcing local packaging workflows to change.

## Windows Installer

`packaging/inno_setup.iss` still targets the local Windows onedir build:

- source directory: `dist\PyMetaboAnalyst\`
- executable: `dist\PyMetaboAnalyst\PyMetaboAnalyst.exe`

Recommended local flow:

```powershell
pyinstaller packaging\pymetabo.spec --clean --noconfirm
```

Then compile `packaging\inno_setup.iss` with Inno Setup Compiler.

## macOS Signing / Notarization

Code signing and notarization are still a separate manual concern from CI packaging.
If production notarization is needed, sign the `.app`, notarize the zipped app, then staple it.

Typical sequence:

```bash
codesign --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
  --options runtime --deep --timestamp dist/PyMetaboAnalyst.app

ditto -c -k --keepParent dist/PyMetaboAnalyst.app dist/PyMetaboAnalyst.zip

xcrun notarytool submit dist/PyMetaboAnalyst.zip \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAMID" \
  --wait

xcrun stapler staple dist/PyMetaboAnalyst.app
```

## Operational Notes

- Do not add Linux back into CI/CD unless the repository is willing to maintain Linux packaging and release validation
- Keep reusable workflow references pinned, not `@main`, if the goal is reproducible CI/CD behavior
- If shared workflow expectations change, update `packaging/pymetabo_release.spec` together with the caller workflow
