@echo off
title Jojo Bot - Stopping
echo Stopping Jojo Bot...
taskkill /fi "WindowTitle eq Jojo Bot - Backend*" /f >nul 2>&1
taskkill /fi "WindowTitle eq Jojo Bot - Frontend*" /f >nul 2>&1
echo Done.
timeout /t 2 /nobreak >nul
