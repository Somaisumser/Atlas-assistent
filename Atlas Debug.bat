@echo off
title Atlas - Debug Mode
cd /d "%~dp0"
echo ==========================================
echo      ATLAS - MODO DEBUG
echo ==========================================
echo.
call venv\Scripts\activate.bat 2>nul
venv\Scripts\python.exe main.py
echo.
echo [DEBUG] Atlas encerrado.
pause
