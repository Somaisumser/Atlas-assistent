@echo off
title Atlas - Atualizador
color 0B
cd /d "%~dp0"

echo.
echo ==========================================
echo      ATLAS - ATUALIZADOR
echo ==========================================
echo.

REM O Git e opcional: se nao estiver instalado, usamos o atualizador em
REM PowerShell, que faz backup dos arquivos locais antes de sobrescrever.
set "USAR_GIT=0"
if exist ".git" (
    where git >nul 2>&1 && set "USAR_GIT=1"
)

if "%USAR_GIT%"=="1" goto via_git
goto via_powershell

:via_git
echo  Verificando atualizacoes via Git...
echo.
git pull origin main
if errorlevel 1 goto git_falhou
echo.
echo  ATUALIZACAO CONCLUIDA!
echo  Reinicie o Atlas.
pause
exit /b 0

:git_falhou
echo.
echo  [ERRO] O Git nao conseguiu atualizar.
echo  Motivo comum: existem alteracoes locais ainda nao commitadas.
echo  Use "git status" e depois "git add . ^&^& git commit -m mensagem".
echo.
echo  Suas alteracoes locais NAO foram apagadas.
pause
exit /b 1

:via_powershell
echo  Git nao encontrado. Usando o atualizador em PowerShell...
echo.
where powershell >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] PowerShell nao encontrado.
    echo  Instale o Git: https://git-scm.com
    echo  Ou baixe manualmente: https://github.com/Somaisumser/Atlas-assistent
    pause
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "%~dp0Atlas-atualizar.ps1"
if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao atualizar.
    pause
    exit /b 1
)

exit /b 0
