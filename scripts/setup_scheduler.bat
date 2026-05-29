@echo off
:: ============================================================
:: setup_scheduler.bat
:: FIFA World Cup 2026 Fantasy — Windows Task Scheduler Setup
:: Run as Administrator
:: ============================================================

SET BASE=C:\Users\siddh\Downloads\HK\FIFA\FIFA World Cup Fantasy Game\scripts
SET PYTHON=python

echo.
echo ==========================================
echo  FIFA Fantasy 2026 — Task Scheduler Setup
echo ==========================================
echo.

:: ── 1. POLL SCHEDULER — every hour ─────────────────────────────────────────
echo [1/4] Registering poll_scheduler (every hour)...
SCHTASKS /CREATE /TN "FIFA_PollScheduler" /TR "%PYTHON% \"%BASE%\poll_scheduler.py\"" ^
  /SC HOURLY /MO 1 /ST 00:00 /F ^
  /RL HIGHEST /RU "%USERNAME%"
IF %ERRORLEVEL% EQU 0 (echo     OK) ELSE (echo     FAILED - run as Administrator)

:: ── 2. STATS FETCHER — every 30 minutes ────────────────────────────────────
echo [2/4] Registering stats_fetcher (every 30 min)...
SCHTASKS /CREATE /TN "FIFA_StatsFetcher" /TR "%PYTHON% \"%BASE%\stats_fetcher.py\"" ^
  /SC MINUTE /MO 30 /ST 00:00 /F ^
  /RL HIGHEST /RU "%USERNAME%"
IF %ERRORLEVEL% EQU 0 (echo     OK) ELSE (echo     FAILED)

:: ── 3. SHEETS UPDATER — every 15 minutes ───────────────────────────────────
echo [3/4] Registering sheets_updater (every 15 min)...
SCHTASKS /CREATE /TN "FIFA_SheetsUpdater" /TR "%PYTHON% \"%BASE%\sheets_updater.py\"" ^
  /SC MINUTE /MO 15 /ST 00:00 /F ^
  /RL HIGHEST /RU "%USERNAME%"
IF %ERRORLEVEL% EQU 0 (echo     OK) ELSE (echo     FAILED)

:: ── 4. DASHBOARD BUILDER — every 60 minutes (background rebuild) ────────────
echo [4/4] Registering dashboard_builder (every 60 min)...
SCHTASKS /CREATE /TN "FIFA_DashboardBuilder" /TR "%PYTHON% \"%BASE%\dashboard_builder.py\" --deploy" ^
  /SC HOURLY /MO 1 /ST 00:30 /F ^
  /RL HIGHEST /RU "%USERNAME%"
IF %ERRORLEVEL% EQU 0 (echo     OK) ELSE (echo     FAILED)

echo.
echo ==========================================
echo  All tasks registered. Verify with:
echo  SCHTASKS /QUERY /FO LIST /TN "FIFA_*"
echo ==========================================
echo.
pause
