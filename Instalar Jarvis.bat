@echo off
chcp 65001 >nul 2>&1
title Jarvis - Instalador
color 0B
cd /d "%~dp0"

echo.
echo =============================================
echo      JARVIS - INSTALADOR AUTOMATICO
echo      Mordomo Virtual Pessoal
echo =============================================
echo.

echo [1/5] Verificando Python...

set PYTHON_CMD=
where python3.11 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python3.11
    goto :python_ok
)
where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYVER=%%a
    echo         Versao encontrada: %PYVER%
    set PYTHON_CMD=python
    goto :python_ok
)

echo.
echo  [ERRO] Python nao encontrado!
echo.
echo  Baixe Python 3.11 em:
echo  https://www.python.org/downloads/release/python-3119/
echo.
echo  IMPORTANTE: Marque "Add Python to PATH" durante a instalacao!
echo.
pause
exit /b 1

:python_ok
echo         Python encontrado: %PYTHON_CMD%
echo.

echo [2/5] Criando ambiente virtual...

if exist "venv" (
    echo         Ambiente virtual ja existe.
) else (
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo  [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
    echo         Ambiente virtual criado!
)
echo.

echo [3/5] Instalando dependencias...
echo         Isso pode demorar alguns minutos...
echo.

call venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet

pip install -r requirements.txt --quiet

if %errorlevel% neq 0 (
    echo.
    echo  [AVISO] Algumas dependencias podem ter falhado.
    echo  Tentando instalacao individual...
    echo.
    pip install SpeechRecognition --quiet
    pip install pyttsx3 --quiet
    pip install edge-tts --quiet
    pip install pygame --quiet
    pip install psutil --quiet
    pip install requests --quiet
    pip install customtkinter --quiet
    pip install ddgs --quiet
    pip install pywin32 --quiet
    pip install screeninfo --quiet
)

echo         Dependencias instaladas!
echo.

echo [4/5] Verificando Ollama...

where ollama >nul 2>&1
if %errorlevel%==0 (
    echo         Ollama encontrado!
    echo.
    echo         Verificando se o Ollama esta rodando...
    tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
    if %errorlevel% neq 0 (
        echo         Iniciando Ollama...
        start "" ollama serve
        timeout /t 3 /nobreak >nul
    ) else (
        echo         Ollama ja esta rodando!
    )
) else (
    echo.
    echo  [AVISO] Ollama nao encontrado!
    echo.
    echo  O Jarvis precisa do Ollama para funcionar.
    echo  Baixe em: https://ollama.com/download
    echo.
    echo  Apos instalar, rode: ollama serve
    echo.
)

echo [5/5] Criando Jarvis.bat...

(
    echo @echo off
    echo chcp 65001 ^>nul 2^>^&1
    echo title Jarvis - Mordomo Virtual
    echo cd /d "%%~dp0"
    echo venv\Scripts\python.exe main.py
    echo pause
) > Jarvis.bat

echo         Jarvis.bat criado!
echo.

echo =============================================
echo        INSTALACAO CONCLUIDA!
echo =============================================
echo.
echo  Para usar o Jarvis:
echo    1. Clique duas vezes em "Jarvis.bat"
echo    2. Ou rode: python main.py
echo.
echo  Comandos de voz:
echo    "Jarvis, abre o discord"
echo    "Jarvis, monitorar pc"
echo    "Jarvis, que horas sao"
echo.
pause
