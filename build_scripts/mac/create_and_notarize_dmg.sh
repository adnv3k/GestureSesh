#!/bin/zsh

###############################################################################
# create_and_notarize_dmg.sh
# Create, sign, notarize, staple, and verify a DMG from a pre-signed, notarized .app
###############################################################################

set -euo pipefail

# --- Config ---
APP_NAME="GestureSesh"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="./${APP_NAME}.dmg"
VOLUME_NAME="GestureSesh"
IDENTITY="${CODESIGN_IDENTITY:?CODESIGN_IDENTITY not set}"
APPLE_ID="${APPLE_ID:?APPLE_ID not set}"
NOTARY_PASSWORD="${NOTARY_PASSWORD:?NOTARY_PASSWORD not set}"
TEAM_ID="${TEAM_ID:?TEAM_ID not set}"

# --- Check required tools ---
for cmd in codesign xcrun hdiutil create-dmg; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "❌ Required command '$cmd' not found. Please install it."; exit 1; }
done

# --- Create DMG with custom layout ---
echo "📦 Creating DMG with custom layout..."
sudo create-dmg \
  --volicon "ui/resources/icons/brush.icns" \
  --volname "GestureSesh Installer" \
  --window-pos 0 900 \
  --window-size 660 350 \
  --icon-size 128 \
  --icon "$APP_PATH" 84 120 \
  --app-drop-link 510 120 \
  --background "ui/resources/dmg_background.png" \
  "$DMG_NAME" \
  "$APP_PATH"

# --- Sign DMG ---
echo "🔏 Signing DMG..."
sudo codesign --force --sign "$IDENTITY" "$DMG_NAME"

# --- Notarize DMG ---
echo "📤 Submitting DMG for notarization..."
NOTARY_RESPONSE=$(sudo xcrun notarytool submit "$DMG_NAME" \
  --apple-id "$APPLE_ID" \
  --password "$NOTARY_PASSWORD" \
  --team-id "$TEAM_ID" \
  --wait 2>&1) || { echo "❌ DMG notarization failed."; echo "$NOTARY_RESPONSE"; exit 1; }
echo "$NOTARY_RESPONSE"
if ! echo "$NOTARY_RESPONSE" | grep -q "Accepted"; then
    echo "❌ DMG notarization failed or was not accepted."
    exit 1
fi

# --- Staple DMG ---
echo "📎 Stapling notarization ticket to DMG..."
sudo xcrun stapler staple "$DMG_NAME"

# --- Verify DMG signature ---
echo "✅ Verifying DMG signature..."
sudo codesign --verify --verbose=2 "$DMG_NAME"

echo "✅ Done! Signed, notarized, and stapled DMG ready at: $DMG_NAME"