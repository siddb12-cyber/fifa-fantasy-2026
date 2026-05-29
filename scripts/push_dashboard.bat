@echo off
title FIFA Fantasy 2026 — Push to GitHub Pages
color 0A

SET FIFA=C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game

cd /d "%FIFA%"

echo.
echo Pushing dashboard redesign to GitHub Pages...
git add -A
git commit -m "Dashboard v2: Premium redesign — index, schedule, stats, match pages"
git push origin main

echo.
echo ============================================================
echo  Done! Live in ~60 seconds at:
echo  https://siddb12-cyber.github.io/fifa-fantasy-2026/
echo ============================================================
echo.
pause
