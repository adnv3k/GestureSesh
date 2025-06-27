#!/usr/bin/env bash

APP_PATH="dist/GestureSesh.app"

# Check if the .app exists
if [[ ! -d "$APP_PATH" ]]; then
    echo "❌ $APP_PATH not found!"
    exit 1
fi

# Try to launch the app
echo "🚀 Launching $APP_PATH..."
open "$APP_PATH"
sleep 5

# Optionally, check if the process is running
if pgrep -f "GestureSesh" > /dev/null; then
    echo "✅ GestureSesh.app launched successfully."
    # Optionally kill the app after test
    pkill -f "GestureSesh"
else
    echo "❌ GestureSesh.app did not launch."
    exit 1
fi
