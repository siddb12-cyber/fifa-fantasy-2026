@echo off
title FIFA Fantasy 2026 — Avatar Generator
color 0A

SET FIFA=C:\Users\siddh\Downloads\HK\FIFA

echo.
echo [1/2] Installing OpenCV (if not already installed)...
pip install opencv-python Pillow numpy --quiet --break-system-packages 2>nul
pip install opencv-python Pillow numpy --quiet 2>nul

echo.
echo [2/2] Generating cartoon avatar cards...
python "%FIFA%\FIFA World Cup Fantasy Game\scripts\avatar_generator.py"

echo.
echo ============================================================
echo  Done! Avatar PNGs saved to:
echo  %FIFA%\FIFA World Cup Fantasy Game\assets\avatars\
echo ============================================================
echo.
pause
