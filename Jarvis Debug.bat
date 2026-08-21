@echo off
title Jarvis - Debug Mode
cd /d "%~dp0"
echo ==========================================
echo      JARVIS - MODO DEBUG
echo ==========================================
echo.
call venv\Scripts\activate.bat 2>nul
venv\Scripts\python.exe main.py
echo.
echo [DEBUG] Jarvis encerrado.
pause
