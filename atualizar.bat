@echo off
chcp 65001 >nul 2>&1
title Jarvis - Atualizador
color 0B
cd /d "%~dp0"

echo.
echo ==========================================
echo      JARVIS - ATUALIZADOR
echo ==========================================
echo.

:: ═══════════════════════════════════════════
:: METODO 1: Git Pull (se tem git)
:: ═══════════════════════════════════════════
if exist ".git" (
    where git >nul 2>&1
    if %errorlevel%==0 (
        echo  Verificando atualizacoes via Git...
        echo.
        git pull origin main
        if %errorlevel%==0 (
            echo.
            echo ==========================================
            echo      ATUALIZACAO CONCLUIDA!
            echo ==========================================
            echo.
            echo  Reinicie o Jarvis para usar a versao nova.
            pause
            exit /b 0
        ) else (
            echo.
            echo  [AVISO] Git falhou. Tentando metodo alternativo...
            echo.
        )
    )
)

:: ═══════════════════════════════════════════
:: METODO 2: Download ZIP (sem git)
:: ═══════════════════════════════════════════
echo  Verificando atualizacoes via download...
echo.

:: Verifica se tem PowerShell
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRO] PowerShell nao encontrado.
    echo  Instale o Git para usar o atualizador automatico.
    echo  Ou baixe manualmente: https://github.com/Somaisumser/jarvis-assistent
    echo.
    pause
    exit /b 1
)

:: Baixa o ZIP
echo  Baixando ultima versao...
echo.

powershell -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/Somaisumser/jarvis-assistent/archive/refs/heads/main.zip' -OutFile '%TEMP%\jarvis-update.zip' -ErrorAction Stop; Write-Host 'OK' } catch { Write-Host 'ERRO' }" 2>nul | find /i "ERRO" >nul
if %errorlevel%==0 (
    echo  [ERRO] Falha ao baixar atualizacao.
    echo  Verifique sua conexao com a internet.
    echo.
    pause
    exit /b 1
)

:: Salva configuracoes do usuario
if exist "lembretes.json" copy "lembretes.json" "%TEMP%\jarvis-lembretes.bak" >nul 2>&1

:: Extrai o ZIP
echo  Instalando atualizacao...
echo.

powershell -Command "try { Expand-Archive -Path '%TEMP%\jarvis-update.zip' -DestinationPath '%TEMP%\jarvis-update' -Force; Copy-Item -Path '%TEMP%\jarvis-update\jarvis-assistent-main\*' -Destination '%~dp0' -Recurse -Force; Remove-Item -Path '%TEMP%\jarvis-update' -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -Path '%TEMP%\jarvis-update.zip' -Force -ErrorAction SilentlyContinue; Write-Host 'OK' } catch { Write-Host 'ERRO' }" 2>nul | find /i "ERRO" >nul

:: Restaura configuracoes do usuario
if exist "%TEMP%\jarvis-lembretes.bak" (
    copy "%TEMP%\jarvis-lembretes.bak" "lembretes.json" >nul 2>&1
    del "%TEMP%\jarvis-lembretes.bak" >nul 2>&1
)

:: Reinstala dependencias novas
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
echo  Reinicie o Jarvis para usar a versao nova.
echo.
pause
