# Build Instructions for ModScan Tool

This document explains how to create standalone executables for different platforms.

## Prerequisites

1. **Icon File**: Place a `icon.png` file (512x512 or 1024x1024 pixels) in the project root
   - The build scripts will automatically convert it to the platform-specific format
   - If no icon is provided, the app will build without an icon

## Building for Different Platforms

**IMPORTANT**: You must build on the target platform. You cannot cross-compile with PyInstaller.

### macOS

1. Open Terminal and navigate to the project directory
2. Run the build script:
   ```bash
   chmod +x build_macos.sh
   ./build_macos.sh
   ```
3. The application will be created at: `dist/ModScan Tool.app`
4. Double-click to run, or drag to Applications folder

**Distribution**:
- For casual sharing: Compress the .app as a .zip
- For professional distribution: Create a DMG or sign with an Apple Developer certificate

### Windows

1. Open Command Prompt and navigate to the project directory
2. Run the build script:
   ```cmd
   build_windows.bat
   ```
3. The executable will be created at: `dist\ModScan Tool.exe`
4. Double-click to run

**Distribution**:
- Simply share the .exe file
- Optionally create an installer using NSIS or Inno Setup

### Linux

1. Open Terminal and navigate to the project directory
2. Run the build script:
   ```bash
   chmod +x build_linux.sh
   ./build_linux.sh
   ```
3. The executable will be created at: `dist/modscan-tool`
4. Run with: `./dist/modscan-tool`

**Distribution**:
- Create a tarball: `tar -czf modscan-tool-linux.tar.gz -C dist modscan-tool`
- Or create a .deb or .rpm package

## Icon Format Requirements

- **macOS**: Automatically converts `icon.png` to `icon.icns`
- **Windows**: Automatically converts `icon.png` to `icon.ico`
- **Linux**: Uses `icon.png` directly

You only need to provide one `icon.png` file!

## Troubleshooting

### Build fails with import errors
- Make sure you're in the virtual environment
- Install missing dependencies: `pip install -r requirements.txt`

### macOS says "app is damaged"
- This happens with unsigned apps on macOS Catalina+
- Right-click the app and select "Open" the first time
- Or run: `xattr -cr "dist/ModScan Tool.app"`

### Windows SmartScreen warning
- This is normal for unsigned executables
- Click "More info" then "Run anyway"
- For professional distribution, get a code signing certificate

### Linux won't run
- Make sure it's executable: `chmod +x dist/modscan-tool`
- Install required libraries if needed: `sudo apt-get install libxcb-xinerama0`

## File Sizes

Approximate sizes for the built applications:
- macOS: ~80-100 MB
- Windows: ~60-80 MB
- Linux: ~70-90 MB

This is normal for PyQt6 applications as they bundle Python and all dependencies.

## Clean Build

If you need to rebuild from scratch:
```bash
rm -rf build dist *.spec icon.icns icon.ico
```

Then run the build script again.
