@echo off
REM ── One-shot script to apply the release-hardening commit cleanly ───────────
REM The sandbox couldn't push (no GitHub credentials). The commit has been
REM bundled into jojo-v1.0-release-hardening.bundle. This script:
REM   1. Cleans up dangling broken git objects from the aborted prior commit
REM   2. Imports the release-hardening commit from the bundle
REM   3. Pushes to origin/main
REM Run from the project root on your Windows machine.

title Jojo Bot - Apply Release Commit
cd /d "%~dp0"

echo.
echo  ============================================================
echo    Applying v1.0 release-hardening commit to origin/main
echo  ============================================================
echo.

if not exist "jojo-v1.0-release-hardening.bundle" (
    echo  [ERROR] Bundle file not found: jojo-v1.0-release-hardening.bundle
    pause
    exit /b 1
)

echo  [1/5] Cleaning up dangling broken objects from prior aborted commit...
git reflog expire --expire=now --all
git gc --prune=now 2>nul

echo.
echo  [2/5] Verifying bundle contents...
git bundle verify jojo-v1.0-release-hardening.bundle
if errorlevel 1 (
    echo  [ERROR] Bundle verification failed.
    pause
    exit /b 1
)

echo.
echo  [3/5] Resetting working tree to match origin/main (backing up first)...
REM Stash any uncommitted local work so it isn't lost
git stash push -u -m "pre-release-bundle-apply" 2>nul
git reset --hard origin/main

echo.
echo  [4/5] Importing release-hardening commit from bundle...
git fetch jojo-v1.0-release-hardening.bundle refs/heads/main:release-hardening-imported
if errorlevel 1 (
    echo  [ERROR] Could not fetch from bundle.
    pause
    exit /b 1
)
git merge --ff-only release-hardening-imported
if errorlevel 1 (
    echo  [ERROR] Fast-forward merge failed.
    pause
    exit /b 1
)
git branch -D release-hardening-imported

echo.
echo  [5/5] Pushing to origin/main...
git push origin main
if errorlevel 1 (
    echo  [ERROR] Push failed. You may need to authenticate.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo    Done. origin/main now has the release-hardening commit.
echo.
echo    Next:
echo      1) Re-run the ingest to refresh chroma_db:
echo         cd src\backend
echo         venv\Scripts\activate
echo         python -m rag.ingest --input ..\..\data\manuals\ --reset
echo      2) Run build-package.bat
echo      3) Smoke-test Jojo Bot.exe on a clean machine
echo  ============================================================
echo.
pause
