@echo off
REM ── Registers "Start Jojo Bot.bat" as a Windows Task Scheduler job ──────────
REM ── that fires automatically every time you log in. ─────────────────────────
REM ── Run this file ONCE. Right-click -> Run as administrator. ────────────────

title Install Jojo Bot Auto-Startup
echo.
echo  Installing Jojo Bot auto-startup via Task Scheduler...
echo.

set SCRIPT_PATH=%~dp0Start Jojo Bot.bat

schtasks /create ^
  /tn "Jojo Bot Auto-Start" ^
  /tr "\"%SCRIPT_PATH%\"" ^
  /sc ONLOGON ^
  /rl HIGHEST ^
  /f

if errorlevel 1 (
    echo.
    echo  [ERROR] Could not create scheduled task.
    echo  Make sure you right-clicked and chose "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   Done! Jojo Bot will now start
echo   automatically every time you log in.
echo.
echo   To remove auto-startup, run:
echo   Uninstall Auto-Startup.bat
echo  ==========================================
echo.
pause
