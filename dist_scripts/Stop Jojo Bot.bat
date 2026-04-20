@echo off
title Jojo Bot - Stopping
echo.
echo  Stopping Jojo Bot...

REM Kill backend and frontend by window title (safe — only targets Jojo Bot windows)
taskkill /fi "WindowTitle eq Jojo Bot Backend*" /f >nul 2>&1
taskkill /fi "WindowTitle eq Jojo Bot Frontend*" /f >nul 2>&1

echo  Jojo Bot stopped.
timeout /t 2 /nobreak >nul
