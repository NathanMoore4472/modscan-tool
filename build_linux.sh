#!/bin/bash
# Build script for Linux

echo "Building ModScan Tool for Linux..."

# Activate virtual environment
source venv/bin/activate

# Install PyInstaller if not already installed
pip install pyinstaller

# Check for icon
if [ -f "icon.png" ]; then
    echo "Using icon.png for application icon"
    ICON_ARG="--icon=icon.png"
else
    echo "No icon.png found, building without icon"
    ICON_ARG=""
fi

# Build the application
pyinstaller --clean --noconfirm \
    --name "modscan-tool" \
    --windowed \
    --onedir \
    --add-data "icon.png:." \
    $ICON_ARG \
    launcher.py

echo ""
echo "Build complete!"
echo "Executable location: dist/modscan-tool"
echo ""
echo "To run: ./dist/modscan-tool"
echo ""
echo "To create a distributable package:"
echo "  tar -czf modscan-tool-linux.tar.gz -C dist modscan-tool"
echo ""
