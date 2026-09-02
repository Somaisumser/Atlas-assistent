@echo off
title Atlas - Instalador
color 0B
cd /d "%~dp0"

echo.
echo =============================================
echo      ATLAS - INSTALADOR AUTOMATICO
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

echo         Python nao encontrado!
echo         Baixando Python 3.11.9...
echo.

:: Baixa o instalador do Python
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python-installer.exe'"

if not exist "%TEMP%\python-installer.exe" (
    echo  [ERRO] Falha ao baixar Python.
    echo  Baixe manualmente em: https://www.python.org/downloads/release/python-3119/
    echo  IMPORTANTE: Marque "Add Python to PATH"!
    pause
    exit /b 1
)

echo         Instalando Python 3.11.9...
echo         (Isso pode demorar alguns minutos)
echo.

:: Instala silenciosamente com PATH
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1
timeout /t 5 /nobreak >nul

:: Limpa o instalador
del "%TEMP%\python-installer.exe" >nul 2>&1

:: Verifica se instalou
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRO] Falha ao instalar Python.
    echo  Reinicie o computador e tente novamente.
    pause
    exit /b 1
)

set PYTHON_CMD=python
echo         Python 3.11.9 instalado com sucesso!

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
    pip install pystray --quiet
    pip install Pillow --quiet
)

:: Verifica se o PyAudio foi instalado
python -c "import pyaudio" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [INFO] PyAudio nao encontrado. Tentando instalar...
    echo.
    pip install pipwin --quiet
    pipwin install pyaudio
    if %errorlevel% neq 0 (
        echo  [AVISO] PyAudio pode ter falhado. O Atlas funciona sem voz.
        echo  Para instalar manualmente: pip install PyAudio
    )
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
    echo  O Atlas precisa do Ollama para funcionar.
    echo  Baixe em: https://ollama.com/download
    echo.
    echo  Apos instalar, rode: ollama serve
    echo.
)

echo [5/5] Criando Atlas.bat...

(
    echo @echo off
    echo title Atlas - Mordomo Virtual
    echo cd /d "%%~dp0"
    echo venv\Scripts\python.exe main.py
    echo pause
) > Atlas.bat

echo         Atlas.bat criado!
echo.

echo =============================================
echo        INSTALACAO CONCLUIDA!
echo =============================================
echo.
echo  Para usar o Atlas:
echo    1. Clique duas vezes em "Atlas.bat"
echo    2. Ou rode: python main.py
echo.
echo  Comandos de voz:
echo    "Atlas, abre o discord"
echo    "Atlas, monitorar pc"
echo    "Atlas, que horas sao"
echo.
pause
