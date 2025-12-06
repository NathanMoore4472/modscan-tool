#!/bin/bash
# Build script for macOS

echo "Building ModScan Tool for macOS..."

# Activate virtual environment
source venv/bin/activate

# Install PyInstaller and dependencies if not already installed
pip install pyinstaller pillow certifi

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
    --onedir \
    --add-data "icon.png:." \
    $ICON_ARG \
    launcher.py

echo ""
echo "Build complete!"
echo "Application location: dist/ModScan Tool.app"
echo ""

# Create DMG for distribution
echo "Creating DMG for distribution..."
DMG_NAME="ModScan-Tool-macOS.dmg"
DMG_TEMP="dist/dmg_temp"
APP_NAME="ModScan Tool.app"

# Remove old DMG if it exists
rm -f "dist/$DMG_NAME"

# Create temporary directory for DMG contents
mkdir -p "$DMG_TEMP"

# Copy the app using ditto (preserves .app bundle structure and symlinks)
ditto "dist/$APP_NAME" "$DMG_TEMP/$APP_NAME"

# Create DMG using hdiutil
hdiutil create -volname "ModScan Tool" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "dist/$DMG_NAME"

# Clean up DMG temp
rm -rf "$DMG_TEMP"

echo "✓ DMG created: dist/$DMG_NAME"
echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo "Upload to GitHub release:"
echo "  • $DMG_NAME"
echo ""
