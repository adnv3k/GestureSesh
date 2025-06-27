#!/usr/bin/env bash

DMG="GestureSesh.dmg"
VOLUME_NAME="GestureSesh"
APP_NAME="GestureSesh.app"
MOUNT_POINT="/Volumes/$VOLUME_NAME"
DEST_APP="/Applications/$APP_NAME"

# 1. Mount the DMG
echo "Mounting DMG..."
hdiutil attach "$DMG" -mountpoint "$MOUNT_POINT"

# 2. Check .app exists
if [[ ! -d "$MOUNT_POINT/$APP_NAME" ]]; then
    echo "❌ $APP_NAME not found in DMG!"
    hdiutil detach "$MOUNT_POINT"
    exit 1
fi

# 3. Copy to /Applications
echo "Copying app to /Applications..."
rm -rf "$DEST_APP"
cp -R "$MOUNT_POINT/$APP_NAME" /Applications/

# 4. Launch the app
echo "Launching app..."
open -a "$DEST_APP"
sleep 5

# 5. Check if running
if pgrep -f "$APP_NAME" > /dev/null; then
    echo "✅ App launched successfully."
    pkill -f "$APP_NAME"
else
    echo "❌ App did not launch."
    hdiutil detach "$MOUNT_POINT"
    exit 1
fi

# 6. Gatekeeper assessment
echo "Checking Gatekeeper status..."
spctl --assess --type exec --verbose "$DEST_APP"

# 7. Clean up
echo "Cleaning up..."
hdiutil detach "$MOUNT_POINT"
rm -rf "$DEST_APP"

echo "✅ DMG test completed successfully."
