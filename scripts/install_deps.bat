@echo off
echo Installing FIFA Fantasy 2026 Python dependencies...
pip install -r "%~dp0requirements.txt"
echo.
echo Done! Run setup_sheets.py to create the Google Sheet.
pause
