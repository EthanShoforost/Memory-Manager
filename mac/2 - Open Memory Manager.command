#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Find Python
PYTHON=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        PYTHON=$cmd
        break
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "Python not found!\n\nPlease run the Setup first." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Check libraries
if ! $PYTHON -c "import requests, bs4, PIL, cv2, numpy" 2>/dev/null; then
    osascript -e 'display dialog "Libraries not installed!\n\nPlease run Setup first." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Minimize Terminal window to Dock
osascript -e 'tell application "Terminal" to set miniaturized of front window to true' &> /dev/null

# Run the app normally
$PYTHON Memory_Manager.py

# Terminal will stay minimized - user can close it when done
exit 0
