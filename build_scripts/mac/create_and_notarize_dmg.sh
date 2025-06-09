#!/usr/bin/env bash

################################################################################
# create_and_notarize_dmg.sh
#
# Creates, signs, notarizes, staples, and verifies a DMG from a pre-built and
# signed .app bundle.
#
# Usage:
# 1. Set the required environment variables:
#    export CODESIGN_IDENTITY="Your Developer ID Application Certificate Name"
#    export APPLE_ID="your-apple-id@example.com"
#    export TEAM_ID="YourTeamID"
#    export NOTARY_PASSWORD="your-app-specific-password"
#
# 2. Run the script from your terminal:
#    ./path/to/create_and_notarize_dmg.sh
#
################################################################################

# --- Script Behavior ---
# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error.
# Print a trace of commands.
set -euo pipefail

# --- Configuration ---
# Get the absolute path to the directory containing this script. This makes the
# script runnable from anywhere.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Assume the project root is two levels up from this script's directory
# (e.g., project_root/build_scripts/mac). Adjust if your structure is different.
PROJECT_ROOT="$SCRIPT_DIR"

# --- User-configurable variables ---
APP_NAME="GestureSesh"
VOLUME_NAME="GestureSesh Installer"

# --- Paths derived from configuration ---
APP_PATH="$PROJECT_ROOT/dist/${APP_NAME}.app"
DMG_NAME="./${APP_NAME}.dmg" # Output DMG in the current working directory
BACKGROUND_IMG="$PROJECT_ROOT/ui/resources/dmg_background.png"

# --- Credentials (sourced from environment variables) ---
# Your "Developer ID Application: Your Name (TEAMID)" certificate.
IDENTITY="${CODESIGN_IDENTITY:?ERROR: CODESIGN_IDENTITY environment variable not set.}"
# Your Apple ID for notarization.
APPLE_ID="${APPLE_ID:?ERROR: APPLE_ID environment variable not set.}"
# An app-specific password for the Apple ID (https://appleid.apple.com).
NOTARY_PASSWORD="${NOTARY_PASSWORD:?ERROR: NOTARY_PASSWORD environment variable not set.}"
# Your Apple Developer Team ID.
TEAM_ID="${TEAM_ID:?ERROR: TEAM_ID environment variable not set.}"


# --- Pre-flight Checks ---
echo "🔎 Checking for required tools and files..."

# Check for command-line tools
for cmd in codesign xcrun hdiutil create-dmg; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "❌ Required command '$cmd' not found. Please install it."; exit 1; }
done

# Check that the source .app and background image actually exist before starting
if [ ! -d "$APP_PATH" ]; then
    echo "❌ Source app bundle not found at: $APP_PATH"
    exit 1
fi
if [ ! -f "$BACKGROUND_IMG" ]; then
    echo "❌ Background image not found at: $BACKGROUND_IMG"
    exit 1
fi

echo "✅ All checks passed. Starting build process..."


# --- 1. Create DMG ---
# The DMG is created with a custom background, icon layout, and a link to /Applications.
# We remove any pre-existing DMG to ensure a clean build.
echo "📦 Creating DMG..."
sudo rm -f "$DMG_NAME"
create-dmg \
  --volname "$VOLUME_NAME" \
  --window-pos 0 900 \
  --window-size 660 350 \
  --icon-size 128 \
  --icon "$APP_NAME.app" 84 120 \
  --hide-extension "$APP_NAME.app" \
  --app-drop-link 510 120 \
  --background "$BACKGROUND_IMG" \
  "$DMG_NAME" \
  "$APP_PATH"


# --- 2. Sign DMG ---
# The DMG itself must be signed for modern versions of macOS.
echo "🔏 Signing DMG..."
sudo codesign --force --sign "$IDENTITY" "$DMG_NAME"


# --- 3. Notarize DMG ---
# Submit the DMG to Apple's notary service. This can take a few minutes.
# `xcrun notarytool` is the modern tool for this.
echo "📤 Submitting DMG for notarization with Apple. This may take a few minutes..."
# Note: Do not run notarytool with sudo. It needs access to your user's keychain.
NOTARY_RESPONSE=$(sudo xcrun notarytool submit "$DMG_NAME" \
  --apple-id "$APPLE_ID" \
  --password "$NOTARY_PASSWORD" \
  --team-id "$TEAM_ID" \
  --wait 2>&1)

# Check if the submission was accepted.
if ! echo "$NOTARY_RESPONSE" | grep -q "Accepted"; then
    echo "❌ DMG notarization failed."
    echo "$NOTARY_RESPONSE"
    exit 1
fi
echo "✅ Notarization accepted by Apple."


# --- 4. Staple DMG ---
# Attach the notarization ticket to the DMG, so Gatekeeper can verify it offline.
echo "📎 Stapling notarization ticket to DMG..."
sudo xcrun stapler staple "$DMG_NAME"


# --- 5. Verify ---
# Final checks to ensure the DMG is signed and notarized correctly.
echo "🔍 Verifying DMG signature and notarization..."

# Verify the code signature.
sudo codesign --verify --verbose=2 "$DMG_NAME"

# Verify that Gatekeeper will accept it.
VERIFICATION_OUTPUT=$(spctl -a -v --type install "$DMG_NAME" 2>&1)

echo "${VERIFICATION_OUTPUT}"

# Check that the verification was successful before declaring victory
if ! echo "${VERIFICATION_OUTPUT}" | grep -q "accepted"; then
    echo "❌ Gatekeeper verification failed. The DMG may not be correctly signed or notarized."
    exit 1
fi

echo "✅ Done! Signed, notarized, and stapled DMG is ready at: $DMG_NAME"
