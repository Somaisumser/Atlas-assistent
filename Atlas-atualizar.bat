@echo off
title Atlas - Atualizador
color 0B
cd /d "%~dp0"

echo.
echo ==========================================
echo      ATLAS - ATUALIZADOR
echo ==========================================
echo.

if exist ".git" (
    where git >nul 2>&1
    if %errorlevel%==0 (
        echo  Verificando atualizacoes via Git...
        echo.
        git pull origin main
        if %errorlevel%==0 (
            echo.
            echo  ATUALIZACAO CONCLUIDA!
            echo  Reinicie o Atlas.
            pause
            exit /b 0
        ) else (
            echo  Git falhou. Tentando download...
            echo.
        )
    )
)

echo  Verificando atualizacoes...
echo.

where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo  PowerShell nao encontrado.
    echo  Instale o Git: https://git-scm.com
    echo  Ou baixe manualmente: https://github.com/Somaisumser/Atlas-assistent
    pause
    exit /b 1
)

echo  Baixando ultima versao...
echo.

powershell -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/Somaisumser/Atlas-assistent/archive/refs/heads/main.zip' -OutFile '%TEMP%\atlas-update.zip' -ErrorAction Stop; Write-Host 'OK' } catch { Write-Host 'ERRO' }" 2>nul | find /i "ERRO" >nul
if %errorlevel%==0 (
    echo  Falha ao baixar. Verifique sua internet.
    pause
    exit /b 1
)

if exist "lembretes.json" copy "lembretes.json" "%TEMP%\atlas-lembretes.bak" >nul 2>&1

echo  Instalando...
echo.

powershell -Command "try { Expand-Archive -Path '%TEMP%\atlas-update.zip' -DestinationPath '%TEMP%\atlas-update' -Force; Copy-Item -Path '%TEMP%\atlas-update\Atlas-assistent-main\*' -Destination '%~dp0' -Recurse -Force; Remove-Item -Path '%TEMP%\atlas-update' -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -Path '%TEMP%\atlas-update.zip' -Force -ErrorAction SilentlyContinue; Write-Host 'OK' } catch { Write-Host 'ERRO' }" 2>nul | find /i "ERRO" >nul

if exist "%TEMP%\atlas-lembretes.bak" (
    copy "%TEMP%\atlas-lembretes.bak" "lembretes.json" >nul 2>&1
    del "%TEMP%\atlas-lembretes.bak" >nul 2>&1
)

if exist "venv" (
    echo  Atualizando dependencias...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet 2>nul
)

echo.
echo ==========================================
echo      ATUALIZACAO CONCLUIDA!
echo ==========================================
echo.
echo  Reinicie o Atlas.
echo.
pause
