#!/usr/bin/env bash


###############################################################################
# GestureSesh macOS Build, Sign, Notarize, and Staple Script
#
# This script automates the process of building, signing, notarizing, and
# stapling a macOS .app bundle for distribution.
#
# USAGE:
#   ./build_and_notarize.sh                # Run the full process (recommended)
#   ./build_and_notarize.sh <step> [...]   # Run one or more specific steps
#
# STEPS (functions you can run individually):
#   check_required_tools
#   clean_build_artifacts
#   build_app
#   fix_permissions
#   clear_extended_attributes
#   sign_app
#   verify_signature
#   gatekeeper_assess
#   create_zip_for_notarization
#   submit_for_notarization
#   staple_ticket
#   finalize_app
#
# EXAMPLES:
#   ./build_and_notarize.sh build_app sign_app verify_signature
#   ./build_and_notarize.sh clean_build_artifacts build_app
#
# ENVIRONMENT VARIABLES (must be set before running):
#   APPLE_ID           # Your Apple Developer Apple ID (email)
#   NOTARY_PASSWORD    # App-specific password for notarization
#   TEAM_ID            # Your Apple Developer Team ID
#   CODESIGN_IDENTITY  # The code signing identity (e.g., "Developer ID Application: ...")
#
# The script will exit with an error if any required variable or tool is missing.
###############################################################################

set -euo pipefail

function on_error {
    local exit_code=$?
    echo "❌ Error on line $1. Exiting with status $exit_code."
    exit $exit_code
}
trap 'on_error $LINENO' ERR

APP_NAME="GestureSesh"
APP_PATH="dist/${APP_NAME}.app"
ZIP_PATH="./${APP_NAME}.zip"
IDENTITY="${CODESIGN_IDENTITY:-}"
BUNDLE_ID="com.gesturesesh.gesturesesh"

: "${APPLE_ID:?APPLE_ID not set}"
: "${NOTARY_PASSWORD:?NOTARY_PASSWORD not set}"
: "${TEAM_ID:?TEAM_ID not set}"
: "${IDENTITY:?CODESIGN_IDENTITY not set}"

function check_command {
    command -v "$1" >/dev/null 2>&1 || { echo "❌ Required command '$1' not found. Please install it."; exit 1; }
}

function check_required_tools {
    echo "🔎 Checking required tools..."
    for cmd in pyinstaller codesign xcrun spctl ditto xattr; do
        check_command "$cmd"
    done
}

function clean_build_artifacts {
    echo "🧹 Cleaning previous build..."
    sudo rm -rf dist build __pycache__ "$ZIP_PATH" || { echo "⚠️ Failed to clean previous build artifacts."; exit 1; }
}

function build_app {
    echo "🏗️ Building .app from spec..."
    sudo pyinstaller GestureSesh_macOS.spec --noconfirm || { echo "❌ PyInstaller build failed."; exit 1; }
    if [[ ! -f "$APP_PATH/Contents/MacOS/$APP_NAME" ]]; then
        echo "❌ Main executable not found after build: $APP_PATH/Contents/MacOS/$APP_NAME"
        exit 1
    fi
}

function fix_permissions {
    echo "🔐 Fixing permissions..."
    sudo chmod +x "$APP_PATH/Contents/MacOS/$APP_NAME" || { echo "❌ Failed to set executable permissions."; exit 1; }
}

function clear_extended_attributes {
    echo "🧼 Clearing extended attributes..."
    sudo xattr -cr "$APP_PATH" || { echo "⚠️ Failed to clear extended attributes."; }
}

function sign_app {
    echo "🔏 Signing app with hardened runtime..."
    sudo codesign --deep --force --verbose \
      --options runtime \
      --sign "$IDENTITY" \
      "$APP_PATH" || { echo "❌ Code signing failed."; exit 1; }
}

function verify_signature {
    echo "✅ Verifying signature..."
    sudo codesign --verify --deep --strict --verbose=2 "$APP_PATH" || { echo "❌ Signature verification failed."; exit 1; }
}

function gatekeeper_assess {
    echo "🛡️ Checking Gatekeeper assessment..."
    sudo spctl --assess --type exec --verbose "$APP_PATH" || echo "⚠️ Gatekeeper assessment failed (may be expected before notarization)."
}

function create_zip_for_notarization {
    echo "📦 Creating ZIP for notarization..."
    sudo ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH" || { echo "❌ Failed to create ZIP archive."; exit 1; }
}

function submit_for_notarization {
    echo "📤 Submitting to Apple notarization..."
    NOTARY_RESPONSE=$(sudo xcrun notarytool submit "$ZIP_PATH" \
      --apple-id "$APPLE_ID" \
      --password "$NOTARY_PASSWORD" \
      --team-id "$TEAM_ID" \
      --wait 2>&1) || { echo "❌ Notarization submission failed."; echo "$NOTARY_RESPONSE"; exit 1; }
    echo "$NOTARY_RESPONSE"
    if ! echo "$NOTARY_RESPONSE" | grep -q "Accepted"; then
        echo "❌ Notarization failed or was not accepted."
        exit 1
    fi
}

function staple_ticket {
    echo "📎 Stapling notarization ticket..."
    sudo xcrun stapler staple "$APP_PATH" || { echo "❌ Stapling failed."; exit 1; }
}

function finalize_app {
    echo "🔧 Fixing permissions..."
    sudo chmod +x "$APP_PATH/Contents/MacOS/$APP_NAME" || { echo "❌ Failed to set executable permissions after stapling."; exit 1; }
    echo "🔐 Re-signing main executable..."
    sudo codesign --force --deep --options runtime --sign "$IDENTITY" "$APP_PATH/Contents/MacOS/$APP_NAME" || { echo "❌ Re-signing main executable failed."; exit 1; }
    echo "🔐 Re-signing app bundle..."
    sudo codesign --force --deep --options runtime --sign "$IDENTITY" "$APP_PATH" || { echo "❌ Re-signing app bundle failed."; exit 1; }
    echo "🧪 Verifying signature..."
    sudo codesign --verify --deep --strict --verbose=2 "$APP_PATH" || { echo "❌ Final signature verification failed."; exit 1; }
    echo "🧩 Gatekeeper assessment..."
    sudo spctl --assess --type exec --verbose "$APP_PATH" || echo "⚠️ Final Gatekeeper assessment failed."
}

function all {
    check_required_tools
    clean_build_artifacts
    build_app
    fix_permissions
    clear_extended_attributes
    sign_app
    verify_signature
    gatekeeper_assess
    create_zip_for_notarization
    submit_for_notarization
    staple_ticket
    finalize_app
    echo "✅ Done! App is built, signed, notarized, and stapled at: $APP_PATH"
}

# CLI argument dispatch
if [[ $# -eq 0 ]]; then
    all
else
    for step in "$@"; do
        if typeset -f "$step" > /dev/null; then
            "$step"
        else
            echo "❌ Unknown step: $step"
            exit 1
        fi
    done
fi
