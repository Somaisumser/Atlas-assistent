@echo off
chcp 65001 >nul 2>&1
title Jarvis - Atualizador
color 0B
cd /d "%~dp0"

echo.
echo  ==========================================
echo       JARVIS - ATUALIZADOR
echo  ==========================================
echo.

:: Verifica se e um repositorio git
if not exist ".git" (
    echo  [ERRO] Esta pasta nao e um repositorio Jarvis.
    echo  Execute "Instalar Jarvis.bat" primeiro.
    echo.
    pause
    exit /b 1
)

echo  Verificando atualizacoes...
echo.

:: Puxa as ultimas atualizacoes
git pull origin main

if %errorlevel%==0 (
    echo.
    echo  ==========================================
    echo       ATUALIZACAO CONCLUIDA!
    echo  ==========================================
    echo.
    echo  Se houve atualizacoes, reinicie o Jarvis.
) else (
    echo.
    echo  [ERRO] Falha ao atualizar.
    echo  Verifique sua conexao com a internet.
)

echo.
pause
