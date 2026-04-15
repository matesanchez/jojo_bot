@echo off
title Uninstall Jojo Bot Auto-Startup
echo.
echo  Removing Jojo Bot from auto-startup...

schtasks /delete /tn "Jojo Bot Auto-Start" /f >nul 2>&1

echo  Done. Jojo Bot will no longer start automatically on login.
echo.
timeout /t 2 /nobreak >nul
