@echo off
REM Build script for Windows

echo Building ModScan Tool for Windows...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install PyInstaller if not already installed
pip install pyinstaller pillow

REM Convert icon if it exists
if exist "icon.png" (
    echo Converting icon to .ico format...
    python -c "from PIL import Image; img = Image.open('icon.png'); img.save('icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])"
    set ICON_ARG=--icon=icon.ico
) else (
    echo No icon.png found, building without icon
    set ICON_ARG=
)

REM Build the application
pyinstaller --clean --noconfirm ^
    --name "ModScan Tool" ^
    --windowed ^
    --onefile ^
    %ICON_ARG% ^
    modscan_tool.py

echo.
echo Build complete!
echo Executable location: dist\ModScan Tool.exe
echo.
echo You can now distribute the .exe file to other Windows computers
echo.
pause
