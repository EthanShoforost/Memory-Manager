#!/bin/bash
echo "========================================"
echo "Memory Manager - First Time Setup"
echo "========================================"
echo ""
echo "Installing required libraries..."
echo ""

pip3 install requests beautifulsoup4 Pillow opencv-python numpy piexif

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "SUCCESS! Setup complete."
    echo "========================================"
    echo ""
    echo "You can now run Memory Manager!"
    echo ""
else
    echo ""
    echo "========================================"
    echo "Installation failed."
    echo "========================================"
    echo ""
    echo "Please try running in Terminal:"
    echo "pip3 install requests beautifulsoup4 Pillow opencv-python numpy piexif"
    echo ""
fi

read -p "Press Enter to close..."
