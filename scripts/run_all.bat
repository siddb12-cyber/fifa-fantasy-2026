@echo off
title FIFA Fantasy 2026 — Full Setup
color 0A
echo.
echo ============================================================
echo  FIFA Fantasy 2026 — Full Setup Runner
echo ============================================================
echo.

SET SCRIPTS=C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game\scripts
SET FIFA=C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game

cd /d "%SCRIPTS%"

echo [STEP 1/5] Installing Python dependencies...
pip install gspread google-auth google-auth-oauthlib selenium webdriver-manager requests pytz Pillow numpy opencv-python 2>&1
echo.

echo [STEP 2/5] Generating cartoon avatars from WhatsApp DPs...
python "%SCRIPTS%\avatar_generator.py"
echo.

echo [STEP 3/5] Setting up Google Sheet (104 matches, 6 tabs)...
python "%SCRIPTS%\setup_sheets.py"
echo.

echo [STEP 4/5] Building demo dashboard...
python "%SCRIPTS%\dashboard_builder.py" --demo
echo.

echo [STEP 5/5] Deploying to GitHub Pages...
cd /d "%FIFA%"
git add -A
git commit -m "FIFA Fantasy 2026: Initial deploy with avatars and demo data"
git push origin main
echo.

echo ============================================================
echo  DONE! Check your GitHub Pages site:
echo  https://siddb12-cyber.github.io/fifa-fantasy-2026/
echo ============================================================
echo.
pause
