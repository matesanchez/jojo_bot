@echo off
setlocal
title Jojo Bot - Build Package

cd /d "%~dp0"

echo.
echo  ============================================================
echo     J O J O   B O T   -   P A C K A G E   B U I L D E R
echo  ============================================================
echo.
echo  This script will:
echo    1. Build the Python backend into a standalone .exe
echo    2. Build the launcher Jojo Bot.exe with the Jojo avatar icon
echo    3. Build the Next.js frontend (standalone mode)
echo    4. Download portable Node.js (if not already cached)
echo    5. Assemble everything into dist\JojoBot-v1.0\
echo    6. Create dist\JojoBot-v1.0.zip
echo.
echo  Expected time: 5-15 minutes (first run takes longer)
echo.
echo  Working directory: %CD%
echo.
pause

REM --- Check prerequisites ---
echo.
echo  [Check] Verifying prerequisites...

where python >nul 2>&1
if not errorlevel 1 goto python_ok
echo  [ERROR] Python not found. Install Python 3.11 from python.org
pause
exit /b 1
:python_ok
echo    python ... OK

where node >nul 2>&1
if not errorlevel 1 goto node_ok
echo  [ERROR] Node.js not found. Install from nodejs.org then re-run.
pause
exit /b 1
:node_ok
echo    node   ... OK

where npm >nul 2>&1
if not errorlevel 1 goto npm_ok
echo  [ERROR] npm not found. Reinstall Node.js from nodejs.org
pause
exit /b 1
:npm_ok
echo    npm    ... OK

echo  [Check] Prerequisites OK.
echo.

REM --- Paths ---
REM Use short 8.3 names to avoid issues with commas/spaces in paths.
REM %~dps0 gives the short-path version of the script's directory.
set "ROOT=%~dps0"
set "BACKEND_DIR=%ROOT%src\backend"
set "FRONTEND_DIR=%ROOT%src\frontend"
set "DIST_DIR=%ROOT%dist\JojoBot-v1.0"
set "NODE_CACHE=%ROOT%dist\_node_cache"

echo  Paths:
echo    ROOT         = %ROOT%
echo    BACKEND_DIR  = %BACKEND_DIR%
echo    FRONTEND_DIR = %FRONTEND_DIR%
echo    DIST_DIR     = %DIST_DIR%
echo.

REM --- Clean previous dist ---
echo  [1/6] Cleaning previous dist...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
echo  Done.
echo.

REM ===================================================================
REM  STEP 1: Build Python backend with PyInstaller
REM ===================================================================
echo  [1/6] Building Python backend (PyInstaller)...
echo  This can take 3-8 minutes on first run.
echo.

cd /d "%BACKEND_DIR%"
echo  Now in: %CD%

if exist "venv\Scripts\activate.bat" goto venv_ok
echo  [ERROR] venv not found. Run this first:
echo    cd src\backend
echo    py -3.11 -m venv venv
echo    venv\Scripts\activate
echo    pip install -r requirements.txt
pause
exit /b 1
:venv_ok

call venv\Scripts\activate.bat

python -c "import PyInstaller" >nul 2>&1
if not errorlevel 1 goto pyinstaller_ok
echo  Installing PyInstaller...
pip install pyinstaller --trusted-host pypi.org --trusted-host files.pythonhosted.org
if not errorlevel 1 goto pyinstaller_ok
echo  [ERROR] Could not install PyInstaller.
deactivate
pause
exit /b 1
:pyinstaller_ok

pyinstaller backend.spec --clean --noconfirm
if not errorlevel 1 goto backend_built
echo  [ERROR] Backend PyInstaller build failed. See output above.
deactivate
pause
exit /b 1
:backend_built

if exist "dist\backend\backend.exe" goto backend_verified
echo  [ERROR] backend.exe was not produced. PyInstaller may have failed silently.
deactivate
pause
exit /b 1
:backend_verified

echo.
echo  [1/6] Backend build complete. (dist\backend\backend.exe exists)
echo.

REM ===================================================================
REM  STEP 2: Build launcher Jojo Bot.exe
REM ===================================================================
echo  [2/6] Building launcher Jojo Bot.exe (native window + avatar icon)...
echo.

python -c "import webview" >nul 2>&1
if not errorlevel 1 goto webview_ok
echo  Installing pywebview...
pip install pywebview --trusted-host pypi.org --trusted-host files.pythonhosted.org
if not errorlevel 1 goto webview_ok
echo  [WARNING] pywebview install failed. Launcher will fall back to default browser.
:webview_ok

cd /d "%ROOT%dist_scripts"
echo  Now in: %CD%

pyinstaller launcher.spec --clean --noconfirm
if not errorlevel 1 goto launcher_built
echo  [ERROR] Launcher PyInstaller build failed. See output above.
deactivate
pause
exit /b 1
:launcher_built

deactivate

if exist "dist\Jojo Bot.exe" goto launcher_verified
echo  [WARNING] Jojo Bot.exe was not produced. Will use .bat fallback.
goto skip_launcher_verify
:launcher_verified
echo  Launcher built: dist_scripts\dist\Jojo Bot.exe
:skip_launcher_verify

echo.
echo  [2/6] Launcher build complete.
echo.

REM ===================================================================
REM  STEP 3: Build Next.js frontend
REM ===================================================================
echo  [3/6] Building Next.js frontend (standalone mode)...
cd /d "%FRONTEND_DIR%"
echo  Now in: %CD%

if exist "node_modules" goto deps_ok
echo  Installing npm dependencies...
call npm install --prefer-offline
if not errorlevel 1 goto deps_ok
echo  [ERROR] npm install failed.
pause
exit /b 1
:deps_ok

set BUILD_STANDALONE=true
call npm run build
set "BUILD_STANDALONE="
if not errorlevel 1 goto frontend_built
echo  [ERROR] Next.js build failed. See output above.
pause
exit /b 1
:frontend_built

if exist ".next\standalone\server.js" goto frontend_verified
echo  [ERROR] Next.js standalone output not found. BUILD_STANDALONE may not be working.
pause
exit /b 1
:frontend_verified

echo.
echo  [3/6] Frontend build complete. (.next\standalone\server.js exists)
echo.

REM ===================================================================
REM  STEP 4: Download portable Node.js
REM ===================================================================
echo  [4/6] Setting up portable Node.js...

set NODE_VERSION=20.11.1
set NODE_ARCH=x64
set "NODE_ZIP=node-v%NODE_VERSION%-win-%NODE_ARCH%.zip"
set "NODE_URL=https://nodejs.org/dist/v%NODE_VERSION%/%NODE_ZIP%"
set "NODE_EXTRACT_DIR=%NODE_CACHE%\node-v%NODE_VERSION%-win-%NODE_ARCH%"

if exist "%NODE_EXTRACT_DIR%\node.exe" goto node_ready
echo  Downloading Node.js v%NODE_VERSION% (portable)...
mkdir "%NODE_CACHE%" 2>nul
powershell -Command "Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_CACHE%\%NODE_ZIP%' -UseBasicParsing"
if not errorlevel 1 goto node_downloaded
echo  [ERROR] Could not download Node.js.
echo  Download manually: %NODE_URL%
echo  Extract to:        %NODE_EXTRACT_DIR%
pause
exit /b 1
:node_downloaded
echo  Extracting...
powershell -Command "Expand-Archive -Path '%NODE_CACHE%\%NODE_ZIP%' -DestinationPath '%NODE_CACHE%' -Force"
del "%NODE_CACHE%\%NODE_ZIP%"
:node_ready

if exist "%NODE_EXTRACT_DIR%\node.exe" goto node_verified
echo  [ERROR] Portable Node.js not found at %NODE_EXTRACT_DIR%\node.exe
pause
exit /b 1
:node_verified
echo  Portable Node.js ready.
echo.

REM ===================================================================
REM  STEP 5: Assemble distribution folder
REM ===================================================================
echo  [5/6] Assembling distribution package...
echo.
cd /d "%ROOT%"
echo  Now in: %CD%
echo  Copying to: %DIST_DIR%
echo.

REM -- Backend --
echo  [5a] Copying backend...
if not exist "%BACKEND_DIR%\dist\backend" echo  [ERROR] Source not found: %BACKEND_DIR%\dist\backend
xcopy /e /i "%BACKEND_DIR%\dist\backend" "%DIST_DIR%\backend"
if not errorlevel 1 goto copy_backend_ok
echo  [ERROR] Failed to copy backend. See error above.
pause
exit /b 1
:copy_backend_ok
echo  OK
echo.

REM -- Frontend --
echo  [5b] Copying frontend...
if not exist "%FRONTEND_DIR%\.next\standalone" echo  [ERROR] Source not found: %FRONTEND_DIR%\.next\standalone
xcopy /e /i "%FRONTEND_DIR%\.next\standalone" "%DIST_DIR%\frontend"
if not errorlevel 1 goto copy_frontend1_ok
echo  [ERROR] Failed to copy frontend standalone. See error above.
pause
exit /b 1
:copy_frontend1_ok

xcopy /e /i "%FRONTEND_DIR%\.next\static" "%DIST_DIR%\frontend\.next\static"
xcopy /e /i "%FRONTEND_DIR%\public" "%DIST_DIR%\frontend\public"
echo  OK
echo.

REM -- Node.js --
echo  [5c] Copying portable Node.js...
xcopy /e /i "%NODE_EXTRACT_DIR%" "%DIST_DIR%\node"
if not errorlevel 1 goto copy_node_ok
echo  [ERROR] Failed to copy Node.js. See error above.
pause
exit /b 1
:copy_node_ok
echo  OK
echo.

REM -- Data --
echo  [5d] Copying knowledge base data...
mkdir "%DIST_DIR%\data" 2>nul
mkdir "%DIST_DIR%\data\manuals" 2>nul
mkdir "%DIST_DIR%\data\user_documents" 2>nul

if not exist "%ROOT%data\manuals" echo  [WARNING] No manuals folder found at %ROOT%data\manuals
if exist "%ROOT%data\manuals" xcopy /e /i "%ROOT%data\manuals" "%DIST_DIR%\data\manuals"
if exist "%ROOT%data\chroma_db" xcopy /e /i "%ROOT%data\chroma_db" "%DIST_DIR%\data\chroma_db"
if exist "%ROOT%data\kb_manifest.json" copy "%ROOT%data\kb_manifest.json" "%DIST_DIR%\data\"
echo  OK
echo.

REM -- Prompts --
echo  [5e] Copying prompts...
if exist "%ROOT%prompts" xcopy /e /i "%ROOT%prompts" "%DIST_DIR%\prompts"
echo  OK
echo.

REM -- Production .env --
echo  [5f] Writing production .env...
echo environment=production> "%DIST_DIR%\backend\.env"
echo chroma_db_path=../data/chroma_db>> "%DIST_DIR%\backend\.env"
echo manuals_dir=../data/manuals>> "%DIST_DIR%\backend\.env"
echo user_documents_dir=../data/user_documents>> "%DIST_DIR%\backend\.env"
echo cors_origins=http://localhost:3000>> "%DIST_DIR%\backend\.env"
echo log_level=info>> "%DIST_DIR%\backend\.env"
echo  OK
echo.

REM -- Launcher and scripts --
echo  [5g] Copying launcher and scripts...
if exist "%ROOT%dist_scripts\dist\Jojo Bot.exe" copy "%ROOT%dist_scripts\dist\Jojo Bot.exe" "%DIST_DIR%\"
if exist "%ROOT%dist_scripts\Start Jojo Bot.bat" copy "%ROOT%dist_scripts\Start Jojo Bot.bat" "%DIST_DIR%\"
if exist "%ROOT%dist_scripts\Stop Jojo Bot.bat" copy "%ROOT%dist_scripts\Stop Jojo Bot.bat" "%DIST_DIR%\"
if exist "%ROOT%dist_scripts\README.txt" copy "%ROOT%dist_scripts\README.txt" "%DIST_DIR%\"
echo  OK
echo.

echo  [5/6] Assembly complete.
echo.

REM ===================================================================
REM  STEP 6: Create ZIP
REM ===================================================================
echo  [6/6] Creating ZIP archive...
cd /d "%ROOT%dist"
powershell -Command "Compress-Archive -Path 'JojoBot-v1.0' -DestinationPath 'JojoBot-v1.0.zip' -Force"
if errorlevel 1 goto zip_failed
echo  Created dist\JojoBot-v1.0.zip
goto zip_done
:zip_failed
echo  [WARNING] ZIP creation failed. The folder is ready - zip it manually.
:zip_done

echo.
echo  ============================================================
echo   BUILD COMPLETE
echo.
echo   Folder:  dist\JojoBot-v1.0\
echo   ZIP:     dist\JojoBot-v1.0.zip
echo.
echo   Colleagues: unzip, double-click Jojo Bot.exe, enter API key.
echo  ============================================================
echo.
pause
