@echo off
setlocal EnableDelayedExpansion
title Jojo Bot - Build Package
cd /d "%~dp0"

echo.
echo  ============================================================
echo     J O J O   B O T   -   P A C K A G E   B U I L D E R
echo  ============================================================
echo.
echo  This script will:
echo    1. Build the Python backend into a standalone .exe
echo    2. Build the launcher "Jojo Bot.exe" with the Jojo avatar icon
echo    3. Build the Next.js frontend (standalone mode)
echo    4. Download portable Node.js (if not already cached)
echo    5. Assemble everything into dist\JojoBot-v1.0\
echo    6. Create dist\JojoBot-v1.0.zip
echo.
echo  Expected time: 5-15 minutes (first run takes longer)
echo.
pause

REM ── Verify prerequisites ─────────────────────────────────────────────────────
echo  [Check] Verifying prerequisites...

where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.11 from python.org
    pause & exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js not found (needed to build frontend).
    echo  Install Node.js from nodejs.org, then re-run this script.
    pause & exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] npm not found.
    pause & exit /b 1
)

echo  [Check] Prerequisites OK.
echo.

REM ── Paths ────────────────────────────────────────────────────────────────────
set ROOT=%~dp0
set BACKEND_DIR=%ROOT%src\backend
set FRONTEND_DIR=%ROOT%src\frontend
set DIST_DIR=%ROOT%dist\JojoBot-v1.0
set NODE_CACHE=%ROOT%dist\_node_cache

REM ── Clean previous dist ───────────────────────────────────────────────────────
echo  [1/6] Cleaning previous dist...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
echo  Done.
echo.

REM ── Step 1: Build Python backend with PyInstaller ────────────────────────────
echo  [1/6] Building Python backend (PyInstaller)...
echo  This can take 3-8 minutes on first run.
echo.

cd /d "%BACKEND_DIR%"

REM Activate venv
if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] venv not found. Run setup first:
    echo    cd src\backend
    echo    py -3.11 -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    pause & exit /b 1
)
call venv\Scripts\activate.bat

REM Install PyInstaller into venv if not present
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo  Installing PyInstaller...
    pip install pyinstaller --trusted-host pypi.org --trusted-host files.pythonhosted.org
)

REM Run PyInstaller for the backend
pyinstaller backend.spec --clean --noconfirm
if errorlevel 1 (
    echo  [ERROR] Backend PyInstaller build failed. Check output above.
    deactivate
    pause & exit /b 1
)

echo.
echo  [1/6] Backend build complete.
echo.

REM ── Step 2: Build launcher "Jojo Bot.exe" with custom icon ───────────────────
echo  [2/6] Building launcher "Jojo Bot.exe" (native window + Jojo avatar icon)...
echo.

REM Install pywebview into the venv (provides Edge WebView2 window support)
python -c "import webview" 2>nul
if errorlevel 1 (
    echo  Installing pywebview (for native app window)...
    pip install pywebview --trusted-host pypi.org --trusted-host files.pythonhosted.org
    if errorlevel 1 (
        echo  [WARNING] pywebview install failed. Launcher will fall back to default browser.
    )
)

cd /d "%ROOT%dist_scripts"

REM Use the same venv that has PyInstaller + pywebview installed
pyinstaller launcher.spec --clean --noconfirm
if errorlevel 1 (
    echo  [ERROR] Launcher PyInstaller build failed. Check output above.
    deactivate
    pause & exit /b 1
)
deactivate

echo.
echo  [2/6] Launcher build complete.
echo.

REM ── Step 3: Build Next.js frontend ───────────────────────────────────────────
echo  [3/6] Building Next.js frontend (standalone mode)...
cd /d "%FRONTEND_DIR%"

REM Install deps if needed
if not exist "node_modules" (
    echo  Installing npm dependencies...
    npm install --prefer-offline
    if errorlevel 1 (
        echo  [ERROR] npm install failed.
        pause & exit /b 1
    )
)

REM Build with standalone output enabled
set BUILD_STANDALONE=true
call npm run build
if errorlevel 1 (
    echo  [ERROR] Next.js build failed. Check output above.
    pause & exit /b 1
)
set BUILD_STANDALONE=

echo.
echo  [3/6] Frontend build complete.
echo.

REM ── Step 4: Download portable Node.js ────────────────────────────────────────
echo  [4/6] Setting up portable Node.js...

set NODE_VERSION=20.11.1
set NODE_ARCH=x64
set NODE_ZIP=node-v%NODE_VERSION%-win-%NODE_ARCH%.zip
set NODE_URL=https://nodejs.org/dist/v%NODE_VERSION%/%NODE_ZIP%
set NODE_EXTRACT_DIR=%NODE_CACHE%\node-v%NODE_VERSION%-win-%NODE_ARCH%

if not exist "%NODE_EXTRACT_DIR%\node.exe" (
    echo  Downloading Node.js v%NODE_VERSION% (portable)...
    mkdir "%NODE_CACHE%" 2>nul
    powershell -Command "Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_CACHE%\%NODE_ZIP%' -UseBasicParsing"
    if errorlevel 1 (
        echo  [ERROR] Could not download Node.js. Check your internet connection.
        echo  Alternatively, download manually:
        echo    %NODE_URL%
        echo  Extract to: %NODE_EXTRACT_DIR%
        pause & exit /b 1
    )
    echo  Extracting...
    powershell -Command "Expand-Archive -Path '%NODE_CACHE%\%NODE_ZIP%' -DestinationPath '%NODE_CACHE%' -Force"
    del "%NODE_CACHE%\%NODE_ZIP%"
)

echo  Portable Node.js ready.
echo.

REM ── Step 5: Assemble the distribution folder ─────────────────────────────────
echo  [5/6] Assembling distribution package...
cd /d "%ROOT%"

REM Copy compiled backend
echo  Copying backend...
xcopy /e /i /q "%BACKEND_DIR%\dist\backend" "%DIST_DIR%\backend"

REM Copy Next.js standalone frontend
echo  Copying frontend...
xcopy /e /i /q "%FRONTEND_DIR%\.next\standalone" "%DIST_DIR%\frontend"
REM Standalone output needs the static assets copied in separately
xcopy /e /i /q "%FRONTEND_DIR%\.next\static" "%DIST_DIR%\frontend\.next\static"
xcopy /e /i /q "%FRONTEND_DIR%\public" "%DIST_DIR%\frontend\public"

REM Copy portable Node.js
echo  Copying portable Node.js...
xcopy /e /i /q "%NODE_EXTRACT_DIR%" "%DIST_DIR%\node"

REM Copy data (manuals + chroma_db)
echo  Copying knowledge base data...
xcopy /e /i /q "%ROOT%data\manuals" "%DIST_DIR%\data\manuals"
if exist "%ROOT%data\chroma_db" (
    xcopy /e /i /q "%ROOT%data\chroma_db" "%DIST_DIR%\data\chroma_db"
)
if exist "%ROOT%data\kb_manifest.json" (
    copy "%ROOT%data\kb_manifest.json" "%DIST_DIR%\data\"
)

REM Create empty user_documents folder
mkdir "%DIST_DIR%\data\user_documents" 2>nul

REM Copy prompts
xcopy /e /i /q "%ROOT%prompts" "%DIST_DIR%\prompts"

REM Write a minimal .env for production settings (no API key!)
echo environment=production> "%DIST_DIR%\backend\.env"
echo chroma_db_path=../data/chroma_db>> "%DIST_DIR%\backend\.env"
echo manuals_dir=../data/manuals>> "%DIST_DIR%\backend\.env"
echo user_documents_dir=../data/user_documents>> "%DIST_DIR%\backend\.env"
echo cors_origins=http://localhost:3000>> "%DIST_DIR%\backend\.env"
echo log_level=info>> "%DIST_DIR%\backend\.env"

REM Copy "Jojo Bot.exe" — the primary launcher with the Jojo avatar icon
echo  Copying Jojo Bot.exe launcher...
copy "%ROOT%dist_scripts\dist\Jojo Bot.exe" "%DIST_DIR%\Jojo Bot.exe"
if errorlevel 1 (
    echo  [WARNING] Could not copy Jojo Bot.exe — check that launcher build succeeded.
)

REM Copy bat fallback scripts (Stop is always useful; Start stays as a fallback)
copy "%ROOT%dist_scripts\Start Jojo Bot.bat" "%DIST_DIR%\Start Jojo Bot.bat"
copy "%ROOT%dist_scripts\Stop Jojo Bot.bat" "%DIST_DIR%\Stop Jojo Bot.bat"
copy "%ROOT%dist_scripts\README.txt" "%DIST_DIR%\README.txt"

echo.
echo  [5/6] Assembly complete.
echo.

REM ── Step 6: Create ZIP ────────────────────────────────────────────────────────
echo  [6/6] Creating ZIP archive...
cd /d "%ROOT%dist"
powershell -Command "Compress-Archive -Path 'JojoBot-v1.0' -DestinationPath 'JojoBot-v1.0.zip' -Force"
if errorlevel 1 (
    echo  [WARNING] Could not create ZIP (PowerShell Compress-Archive failed).
    echo  The dist\JojoBot-v1.0\ folder is ready — zip it manually.
) else (
    echo  Created dist\JojoBot-v1.0.zip
)

echo.
echo  ============================================================
echo   BUILD COMPLETE
echo.
echo   Distribution folder: dist\JojoBot-v1.0\
echo   ZIP archive:         dist\JojoBot-v1.0.zip
echo.
echo   Share the ZIP with colleagues. Each person:
echo     1. Unzip anywhere
echo     2. Double-click "Jojo Bot.exe"  ^<-- shows Jojo icon in Explorer
echo     3. Click the gear icon (Settings)
echo     4. Enter their Anthropic API key
echo     5. Start chatting!
echo.
echo   (Fallback: "Start Jojo Bot.bat" does the same thing without the icon)
echo  ============================================================
echo.
pause
