@echo off
title Jojo Bot
cd /d "%~dp0"

echo.
echo  ==========================================
echo        J O J O   B O T   v1.0
echo       Purification Expert - Starting
echo  ==========================================
echo.

REM ── 1. Start the backend ─────────────────────────────────────────────────────
echo  [1/2] Starting Jojo Bot backend...
start "Jojo Bot - Backend" cmd /k "title Jojo Bot Backend && cd /d "%~dp0backend" && backend.exe"

REM Give the backend time to load ChromaDB and open the database
timeout /t 6 /nobreak >nul

REM ── 2. Start the frontend ────────────────────────────────────────────────────
echo  [2/2] Starting Jojo Bot frontend...
start "Jojo Bot - Frontend" cmd /k "title Jojo Bot Frontend && cd /d "%~dp0frontend" && "%~dp0node\node.exe" server.js"

REM Wait for frontend to be ready, then open the browser
timeout /t 4 /nobreak >nul

echo.
echo  ==========================================
echo   Jojo Bot is ready!
echo   Opening http://localhost:3000 ...
echo  ==========================================
echo.

start "" "http://localhost:3000"

echo  Two windows are running (Backend + Frontend).
echo  Close this window — the servers keep running in their own windows.
echo  To stop Jojo Bot, double-click "Stop Jojo Bot.bat"
echo.
echo  First time? Click the gear icon in the top-right corner of
echo  the app to enter your Anthropic API key.
echo.
