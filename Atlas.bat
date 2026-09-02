@echo off
title Atlas - Mordomo Virtual
cd /d "%~dp0"

:: Cria um launcher VBS que esconde o CMD
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%~dp0"
    echo WshShell.Run "venv\Scripts\python.exe main.py", 0, False
) > "%TEMP%\atlas_launch.vbs"

wscript "%TEMP%\atlas_launch.vbs"
del "%TEMP%\atlas_launch.vbs" >nul 2>&1
