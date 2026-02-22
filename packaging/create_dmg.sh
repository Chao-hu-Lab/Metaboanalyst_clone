#!/bin/bash
# macOS DMG 建立腳本
# 前置: pyinstaller packaging/pymetabo_mac.spec --noconfirm --clean
# 注意: 不進行 Apple 簽署/公證，使用者需自行處理隱私權驗證
#       (System Preferences > Security & Privacy > Open Anyway)

set -e

APP_NAME="PyMetaboAnalyst"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}.dmg"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run pyinstaller first."
    exit 1
fi

# 移除舊 DMG
rm -f "$DMG_PATH"

# 建立 DMG
if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "$APP_NAME" \
        --window-size 600 400 \
        --icon-size 100 \
        --app-drop-link 400 200 \
        --icon "${APP_NAME}.app" 200 200 \
        "$DMG_PATH" "$APP_PATH"
else
    # fallback: 使用 hdiutil
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "$APP_PATH" \
        -ov -format UDZO \
        "$DMG_PATH"
fi

echo "DMG created: $DMG_PATH"
echo ""
echo "NOTE: This app is NOT signed or notarized."
echo "Users need to right-click > Open, or allow it in:"
echo "  System Preferences > Security & Privacy > Open Anyway"
