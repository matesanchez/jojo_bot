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
echo    2. Build the launcher Jojo Bot.exe with the Jojo avatar icon
echo    3. Build the Next.js frontend (standalone mode)
echo    4. Download portable Node.js (if not already cached)
echo    5. Assemble everything into dist\JojoBot-v1.0\
echo    6. Create dist\JojoBot-v1.0.zip
echo.
echo  Expected time: 5-15 minutes (first run takes longer)
echo.
pause

REM --- Check prerequisites ---
echo  [Check] Verifying prerequisites...

where python >nul 2>&1
if not errorlevel 1 goto python_ok
echo.
echo  [ERROR] Python not found. Install Python 3.11 from python.org
echo.
pause
exit /b 1
:python_ok

where node >nul 2>&1
if not errorlevel 1 goto node_ok
echo.
echo  [ERROR] Node.js not found. Install from nodejs.org then re-run.
echo.
pause
exit /b 1
:node_ok

where npm >nul 2>&1
if not errorlevel 1 goto npm_ok
echo.
echo  [ERROR] npm not found. Reinstall Node.js from nodejs.org
echo.
pause
exit /b 1
:npm_ok

echo  [Check] Prerequisites OK.
echo.

REM --- Paths ---
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%src\backend"
set "FRONTEND_DIR=%ROOT%src\frontend"
set "DIST_DIR=%ROOT%dist\JojoBot-v1.0"
set "NODE_CACHE=%ROOT%dist\_node_cache"

REM --- Clean previous dist ---
echo  [1/6] Cleaning previous dist...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
echo  Done.
echo.

REM --- Step 1: Build Python backend with PyInstaller ---
echo  [1/6] Building Python backend (PyInstaller)...
echo  This can take 3-8 minutes on first run.
echo.

cd /d "%BACKEND_DIR%"

if exist "venv\Scripts\activate.bat" goto venv_ok
echo.
echo  [ERROR] venv not found. Run this first:
echo    cd src\backend
echo    py -3.11 -m venv venv
echo    venv\Scripts\activate
echo    pip install -r requirements.txt
echo.
pause
exit /b 1
:venv_ok

call venv\Scripts\activate.bat

python -c "import PyInstaller" >nul 2>&1
if not errorlevel 1 goto pyinstaller_ok
echo  Installing PyInstaller...
pip install pyinstaller --trusted-host pypi.org --trusted-host files.pythonhosted.org
:pyinstaller_ok

pyinstaller backend.spec --clean --noconfirm
if not errorlevel 1 goto backend_built
echo.
echo  [ERROR] Backend PyInstaller build failed. See output above.
echo.
deactivate
pause
exit /b 1
:backend_built

echo.
echo  [1/6] Backend build complete.
echo.

REM --- Step 2: Build launcher Jojo Bot.exe ---
echo  [2/6] Building launcher Jojo Bot.exe (native window + avatar icon)...
echo.

python -c "import webview" >nul 2>&1
if not errorlevel 1 goto webview_ok
echo  Installing pywebview...
pip install pywebview --trusted-host pypi.org --trusted-host files.pythonhosted.org
:webview_ok

cd /d "%ROOT%dist_scripts"

pyinstaller launcher.spec --clean --noconfirm
if not errorlevel 1 goto launcher_built
echo.
echo  [ERROR] Launcher PyInstaller build failed. See output above.
echo.
deactivate
pause
exit /b 1
:launcher_built

deactivate
echo.
echo  [2/6] Launcher build complete.
echo.

REM --- Step 3: Build Next.js frontend ---
echo  [3/6] Building Next.js frontend (standalone mode)...
cd /d "%FRONTEND_DIR%"

if exist "node_modules" goto deps_ok
echo  Installing npm dependencies...
npm install --prefer-offline
if not errorlevel 1 goto deps_ok
echo.
echo  [ERROR] npm install failed.
echo.
pause
exit /b 1
:deps_ok

set BUILD_STANDALONE=true
call npm run build
set BUILD_STANDALONE=
if not errorlevel 1 goto frontend_built
echo.
echo  [ERROR] Next.js build failed. See output above.
echo.
pause
exit /b 1
:frontend_built

echo.
echo  [3/6] Frontend build complete.
echo.

REM --- Step 4: Download portable Node.js ---
echo  [4/6] Setting up portable Node.js...

set NODE_VERSION=20.11.1
set NODE_ARCH=x64
set NODE_ZIP=node-v%NODE_VERSION%-win-%NODE_ARCH%.zip
set NODE_URL=https://nodejs.org/dist/v%NODE_VERSION%/%NODE_ZIP%
set NODE_EXTRACT_DIR=%NODE_CACHE%\node-v%NODE_VERSION%-win-%NODE_ARCH%

if exist "%NODE_EXTRACT_DIR%\node.exe" goto node_ready
echo  Downloading Node.js v%NODE_VERSION% (portable)...
mkdir "%NODE_CACHE%" 2>nul
powershell -Command "Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_CACHE%\%NODE_ZIP%' -UseBasicParsing"
if not errorlevel 1 goto node_downloaded
echo.
echo  [ERROR] Could not download Node.js. Check your internet connection.
echo  Or download manually: %NODE_URL%
echo  Then extract to:      %NODE_EXTRACT_DIR%
echo.
pause
exit /b 1
:node_downloaded
echo  Extracting...
powershell -Command "Expand-Archive -Path '%NODE_CACHE%\%NODE_ZIP%' -DestinationPath '%NODE_CACHE%' -Force"
del "%NODE_CACHE%\%NODE_ZIP%"
:node_ready
echo  Portable Node.js ready.
echo.

REM --- Step 5: Assemble distribution folder ---
echo  [5/6] Assembling distribution package...
cd /d "%ROOT%"

echo  Copying backend...
xcopy /e /i /q "%BACKEND_DIR%\dist\backend" "%DIST_DIR%\backend"

echo  Copying frontend...
xcopy /e /i /q "%FRONTEND_DIR%\.next\standalone" "%DIST_DIR%\frontend"
xcopy /e /i /q "%FRONTEND_DIR%\.next\static" "%DIST_DIR%\frontend\.next\static"
xcopy /e /i /q "%FRONTEND_DIR%\public" "%DIST_DIR%\frontend\public"

echo  Copying portable Node.js...
xcopy /e /i /q "%NODE_EXTRACT_DIR%" "%DIST_DIR%\node"

echo  Copying knowledge base data...
xcopy /e /i /q "%ROOT%data\manuals" "%DIST_DIR%\data\manuals"
if exist "%ROOT%data\chroma_db" xcopy /e /i /q "%ROOT%data\chroma_db" "%DIST_DIR%\data\chroma_db"
if exist "%ROOT%data\kb_manifest.json" copy "%ROOT%data\kb_manifest.json" "%DIST_DIR%\data\"

mkdir "%DIST_DIR%\data\user_documents" 2>nul

xcopy /e /i /q "%ROOT%prompts" "%DIST_DIR%\prompts"

REM Write production .env (no API key)
echo environment=production> "%DIST_DIR%\backend\.env"
echo chroma_db_path=../data/chroma_db>> "%DIST_DIR%\backend\.env"
echo manuals_dir=../data/manuals>> "%DIST_DIR%\backend\.env"
echo user_documents_dir=../data/user_documents>> "%DIST_DIR%\backend\.env"
echo cors_origins=http://localhost:3000>> "%DIST_DIR%\backend\.env"
echo log_level=info>> "%DIST_DIR%\backend\.env"

echo  Copying launcher...
copy "%ROOT%dist_scripts\dist\Jojo Bot.exe" "%DIST_DIR%\Jojo Bot.exe"
if errorlevel 1 echo  [WARNING] Could not copy Jojo Bot.exe

copy "%ROOT%dist_scripts\Start Jojo Bot.bat" "%DIST_DIR%\Start Jojo Bot.bat"
copy "%ROOT%dist_scripts\Stop Jojo Bot.bat" "%DIST_DIR%\Stop Jojo Bot.bat"
copy "%ROOT%dist_scripts\README.txt" "%DIST_DIR%\README.txt"

echo.
echo  [5/6] Assembly complete.
echo.

REM --- Step 6: Create ZIP ---
echo  [6/6] Creating ZIP archive...
cd /d "%ROOT%dist"
powershell -Command "Compress-Archive -Path 'JojoBot-v1.0' -DestinationPath 'JojoBot-v1.0.zip' -Force"
if errorlevel 1 goto zip_failed
echo  Created dist\JojoBot-v1.0.zip
goto zip_done
:zip_failed
echo  [WARNING] ZIP creation failed - the dist\JojoBot-v1.0\ folder is ready, zip it manually.
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
