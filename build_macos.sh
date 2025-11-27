#!/bin/bash
# Build script for macOS

echo "Building ModScan Tool for macOS..."

# Activate virtual environment
source venv/bin/activate

# Install PyInstaller if not already installed
pip install pyinstaller pillow

# Convert icon if it exists
if [ -f "icon.png" ]; then
    echo "Converting icon to .icns format..."
    python3 << EOF
from PIL import Image
import os

# Create iconset directory
iconset_dir = "icon.iconset"
os.makedirs(iconset_dir, exist_ok=True)

# Load the icon
img = Image.open("icon.png")

# Generate different sizes for macOS
sizes = [16, 32, 64, 128, 256, 512]
for size in sizes:
    # Standard resolution
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(f"{iconset_dir}/icon_{size}x{size}.png")
    # Retina resolution
    resized = img.resize((size*2, size*2), Image.Resampling.LANCZOS)
    resized.save(f"{iconset_dir}/icon_{size}x{size}@2x.png")

print("Icon conversion complete")
EOF

    # Convert iconset to icns
    iconutil -c icns icon.iconset
    rm -rf icon.iconset
    ICON_ARG="--icon=icon.icns"
else
    echo "No icon.png found, building without icon"
    ICON_ARG=""
fi

# Build the application
pyinstaller --clean --noconfirm \
    --name "ModScan Tool" \
    --windowed \
    --onefile \
    $ICON_ARG \
    modscan_tool.py

echo ""
echo "Build complete!"
echo "Application location: dist/ModScan Tool.app"
echo ""
echo "To create a DMG for distribution:"
echo "  1. Create a folder called 'ModScan Tool Installer'"
echo "  2. Copy 'dist/ModScan Tool.app' into it"
echo "  3. Right-click the folder and select 'Compress'"
echo ""
