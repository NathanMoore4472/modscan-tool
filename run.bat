@echo off
REM Launch script for Modbus Scanner Tool (Windows)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application
python modscan_tool.py
