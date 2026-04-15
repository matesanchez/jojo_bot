@echo off
title Jojo Bot
cd /d "%~dp0"

echo.
echo  ==========================================
echo        J O J O   B O T   v1.0
echo       Purification Expert - Starting
echo  ==========================================
echo.

REM ── 1. Build frontend if this is the first run ──────────────────────────────
if not exist "src\frontend\.next" (
    echo  [Setup] Building frontend for the first time...
    echo  [Setup] This takes about 1-2 minutes and only happens once.
    echo.
    cd src\frontend
    call npm install --prefer-offline 2>/dev/null
    call npm run build
    if errorlevel 1 (
        echo.
        echo  [ERROR] Frontend build failed. Check that Node.js is installed.
        pause
        exit /b 1
    )
    cd ..\..
    echo.
)

REM ── 2. Start the backend ─────────────────────────────────────────────────────
echo  [1/2] Starting backend  (http://localhost:8000) ...
start "Jojo Bot - Backend" cmd /k "title Jojo Bot - Backend && cd /d "%~dp0src\backend" && venv\Scripts\activate && python main.py"

REM Give the backend a moment to initialise ChromaDB and load the vector store
timeout /t 5 /nobreak >/dev/null

REM ── 3. Start the frontend ────────────────────────────────────────────────────
echo  [2/2] Starting frontend (http://localhost:3000) ...
start "Jojo Bot - Frontend" cmd /k "title Jojo Bot - Frontend && cd /d "%~dp0src\frontend" && npm start"

REM Wait for frontend to be ready, then open the browser
timeout /t 4 /nobreak >/dev/null

echo.
echo  ==========================================
echo   Jojo Bot is ready!
echo   Opening http://localhost:3000 ...
echo  ==========================================
echo.

start "" "http://localhost:3000"

echo  Two windows opened (Backend + Frontend).
echo  Close those windows to shut down Jojo Bot.
echo.
echo  First time? Click the gear icon in the top-right corner
echo  to configure your Anthropic API key.
echo.
pause
