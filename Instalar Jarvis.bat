@echo off
chcp 65001 >nul 2>&1
title Jarvis - Instalador
color 0B

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     JARVIS - INSTALADOR AUTOMATICO      ║
echo  ║     Mordomo Virtual Pessoal             ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ═══════════════════════════════════════════
:: 1. VERIFICAR PYTHON
:: ═══════════════════════════════════════════
echo [1/5] Verificando Python...

:: Tenta python3.11 primeiro, depois python
set PYTHON_CMD=
where python3.11 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python3.11
    goto :python_ok
)
where python >nul 2>&1
if %errorlevel%==0 (
    :: Verifica se e Python 3.11+
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

:: ═══════════════════════════════════════════
:: 2. CRIAR VIRTUAL ENVIRONMENT
:: ═══════════════════════════════════════════
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

:: ═══════════════════════════════════════════
:: 3. INSTALAR DEPENDENCIAS
:: ═══════════════════════════════════════════
echo [3/5] Instalando dependencias...
echo         Isso pode demorar alguns minutos...
echo.

call venv\Scripts\activate.bat

:: Atualiza pip primeiro
python -m pip install --upgrade pip --quiet

:: Instala todas as dependencias
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

:: ═══════════════════════════════════════════
:: 4. VERIFICAR OLLAMA
:: ═══════════════════════════════════════════
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

:: ═══════════════════════════════════════════
:: 5. CRIAR ATALHO
:: ═══════════════════════════════════════════
echo [5/5] Criando Jarvis.bat...

(
    echo @echo off
    echo chcp 65001 ^>nul 2^>^&1
    echo title Jarvis - Mordomo Virtual
    echo cd /d "%%~dp0"
    echo call venv\Scripts\activate.bat
    echo python main.py
    echo pause
) > Jarvis.bat

echo         Jarvis.bat criado!
echo.

:: ═══════════════════════════════════════════
:: CONCLUSAO
:: ═══════════════════════════════════════════
echo  ╔══════════════════════════════════════════╗
echo  ║        INSTALACAO CONCLUIDA!            ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Para usar o Jarvis:
echo    1. Clique duas vezes em "Jarvis.bat"
echo    2. Ou rode: venv\Scripts\activate ^& python main.py
echo.
echo  Comandos de voz:
echo    "Jarvis, abre o discord"
echo    "Jarvis, monitorar pc"
echo    "Jarvis, que horas sao"
echo.
pause
