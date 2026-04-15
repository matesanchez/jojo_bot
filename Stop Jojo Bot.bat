@echo off
title Jojo Bot - Stopping
echo Stopping Jojo Bot...
taskkill /fi "WindowTitle eq Jojo Bot - Backend*" /f >/dev/null 2>&1
taskkill /fi "WindowTitle eq Jojo Bot - Frontend*" /f >/dev/null 2>&1
echo Done.
timeout /t 2 /nobreak >/dev/null
