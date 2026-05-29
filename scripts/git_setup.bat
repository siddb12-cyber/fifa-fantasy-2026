@echo off
title FIFA Fantasy 2026 — Git Setup
color 0A

SET FIFA=C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game

cd /d "%FIFA%"

echo.
echo [1/5] Initializing git repo in project folder...
git init

echo.
echo [2/5] Setting remote to your GitHub Pages repo...
git remote remove origin 2>nul
git remote add origin https://github.com/siddb12-cyber/fifa-fantasy-2026.git

echo.
echo [3/5] Configuring git user (if not set globally)...
git config user.email "siddb12@gmail.com"
git config user.name "Sidhant Budhkar"

echo.
echo [4/5] Running demo dashboard build...
python "%FIFA%\scripts\dashboard_builder.py" --demo

echo.
echo [5/5] Staging all files and pushing to GitHub Pages...
git add -A
git commit -m "FIFA Fantasy 2026: Full dashboard deploy with avatars"
git branch -M main
git push -u origin main --force

echo.
echo ============================================================
echo  Done! Site should be live in ~60 seconds at:
echo  https://siddb12-cyber.github.io/fifa-fantasy-2026/
echo ============================================================
echo.
pause
