@echo off
title Jarvis - Mordomo Virtual
cd /d "%~dp0"

:: Cria um launcher VBS que esconde o CMD
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%~dp0"
    echo WshShell.Run "venv\Scripts\python.exe main.py", 0, False
) > "%TEMP%\jarvis_launch.vbs"

wscript "%TEMP%\jarvis_launch.vbs"
del "%TEMP%\jarvis_launch.vbs" >nul 2>&1
