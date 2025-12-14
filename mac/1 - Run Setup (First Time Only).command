#!/bin/bash

# Disable Terminal save prompt
exec 2>&1

clear
cat << "LOGO"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║           MEMORY MANAGER - SETUP WIZARD              ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
LOGO

echo ""
echo "This will set up Memory Manager on your Mac."
echo "It only needs to be done once!"
echo ""
read -p "Press Enter to begin setup..."
clear

# Step 1: Check for Python
cat << "LOGO"
╔═══════════════════════════════════════════════════════╗
║  Step 1/2: Checking for Python...                    ║
╚═══════════════════════════════════════════════════════╝
LOGO
echo ""

PYTHON=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON=$cmd
            echo "✅ Found: Python $version"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python 3.10 or newer is required!"
    echo ""
    echo "Please install Python from: https://www.python.org/downloads/"
    echo "Then run this setup again."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
sleep 1

# Step 2: Install libraries
clear
cat << "LOGO"
╔═══════════════════════════════════════════════════════╗
║  Step 2/2: Installing required libraries...          ║
╚═══════════════════════════════════════════════════════╝
LOGO
echo ""
echo "This may take 2-3 minutes. Please wait..."
echo ""

PACKAGES=("requests" "beautifulsoup4" "Pillow" "opencv-python" "numpy")
IMPORT_NAMES=("requests" "bs4" "PIL" "cv2" "numpy")

MISSING=()
for i in "${!PACKAGES[@]}"; do
    if ! $PYTHON -c "import ${IMPORT_NAMES[$i]}" 2>/dev/null; then
        MISSING+=("${PACKAGES[$i]}")
    fi
done

if [ ${#MISSING[@]} -eq 0 ]; then
    echo "✅ All libraries already installed!"
else
    total=${#MISSING[@]}
    current=0
    
    for pkg in "${MISSING[@]}"; do
        current=$((current + 1))
        echo "[$current/$total] Installing $pkg..."
        $PYTHON -m pip install --user --quiet "$pkg" 2>&1 | grep -v "WARNING" || true
        
        if [ $? -eq 0 ]; then
            echo "          ✅ Done"
        else
            echo "          ⚠️  May have failed (will try to continue)"
        fi
    done
fi

echo ""
sleep 1

# Done!
clear
cat << "LOGO"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║                 ✅ SETUP COMPLETE!                    ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
LOGO
echo ""
echo "Memory Manager is ready to use!"
echo ""
echo "To launch Memory Manager:"
echo "  → Double-click 'Open Memory Manager'"
echo ""
echo "You can delete this setup file - you won't need it again."
echo ""
echo "Closing in 2 seconds..."
sleep 2

# Force close without prompt
killall Terminal &> /dev/null
exit 0
