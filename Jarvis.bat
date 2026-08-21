@echo off
chcp 65001 >nul 2>&1
title Jarvis - Mordomo Virtual
cd /d "%~dp0"
call venv\Scripts\activate.bat 2>nul
venv\Scripts\python.exe main.py
pause
