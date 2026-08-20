# Jarvis - Instalador PowerShell
# Rode: powershell -ExecutionPolicy Bypass -File instalar.ps1

$ErrorActionPreference = "Continue"
$Pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Pasta

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "       JARVIS - INSTALADOR AUTOMATICO" -ForegroundColor Cyan
Write-Host "       Mordomo Virtual Pessoal" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# ═══════════════════════════════════════════
# 1. VERIFICAR PYTHON
# ═══════════════════════════════════════════
Write-Host "[1/5] Verificando Python..." -ForegroundColor Yellow

$PythonCmd = $null

# Tenta python3.11
if (Get-Command "python3.11" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3.11"
}
# Tenta python
elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
}

if (-not $PythonCmd) {
    Write-Host "  [ERRO] Python nao encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Baixe Python 3.11 em:" -ForegroundColor White
    Write-Host "  https://www.python.org/downloads/release/python-3119/" -ForegroundColor Green
    Write-Host ""
    Write-Host "  IMPORTANTE: Marque 'Add Python to PATH'!" -ForegroundColor Yellow
    Read-Host "Pressione Enter para sair"
    exit 1
}

$pyVersion = & $PythonCmd --version 2>&1
Write-Host "  Python encontrado: $pyVersion" -ForegroundColor Green
Write-Host ""

# ═══════════════════════════════════════════
# 2. CRIAR VIRTUAL ENVIRONMENT
# ═══════════════════════════════════════════
Write-Host "[2/5] Criando ambiente virtual..." -ForegroundColor Yellow

if (Test-Path "venv") {
    Write-Host "  Ambiente virtual ja existe." -ForegroundColor Gray
} else {
    & $PythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERRO] Falha ao criar venv!" -ForegroundColor Red
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    Write-Host "  Ambiente virtual criado!" -ForegroundColor Green
}
Write-Host ""

# ═══════════════════════════════════════════
# 3. INSTALAR DEPENDENCIAS
# ═══════════════════════════════════════════
Write-Host "[3/5] Instalando dependencias..." -ForegroundColor Yellow
Write-Host "  Isso pode demorar alguns minutos..." -ForegroundColor Gray

& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet 2>$null
pip install -r requirements.txt --quiet 2>$null

Write-Host "  Dependencias instaladas!" -ForegroundColor Green
Write-Host ""

# ═══════════════════════════════════════════
# 4. VERIFICAR OLLAMA
# ═══════════════════════════════════════════
Write-Host "[4/5] Verificando Ollama..." -ForegroundColor Yellow

if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    Write-Host "  Ollama encontrado!" -ForegroundColor Green
    
    $ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if (-not $ollamaRunning) {
        Write-Host "  Iniciando Ollama..." -ForegroundColor Gray
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  Ollama ja esta rodando!" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "  [AVISO] Ollama nao encontrado!" -ForegroundColor Yellow
    Write-Host "  Baixe em: https://ollama.com/download" -ForegroundColor White
    Write-Host ""
}

# ═══════════════════════════════════════════
# 5. CRIAR ATALHO
# ═══════════════════════════════════════════
Write-Host "[5/5] Criando Jarvis.bat..." -ForegroundColor Yellow

$batContent = @"
@echo off
chcp 65001 >nul 2>&1
title Jarvis - Mordomo Virtual
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
pause
"@

Set-Content -Path "Jarvis.bat" -Value $batContent -Encoding UTF8
Write-Host "  Jarvis.bat criado!" -ForegroundColor Green
Write-Host ""

# ═══════════════════════════════════════════
# CONCLUSAO
# ═══════════════════════════════════════════
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "       INSTALACAO CONCLUIDA!" -ForegroundColor Green
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Para usar o Jarvis:" -ForegroundColor White
Write-Host "    1. Clique duas vezes em 'Jarvis.bat'" -ForegroundColor Green
Write-Host "    2. Ou rode: python main.py" -ForegroundColor Green
Write-Host ""
Write-Host "  Comandos de voz:" -ForegroundColor White
Write-Host "    'Jarvis, abre o discord'" -ForegroundColor Gray
Write-Host "    'Jarvis, monitorar pc'" -ForegroundColor Gray
Write-Host "    'Jarvis, que horas sao'" -ForegroundColor Gray
Write-Host ""
Read-Host "Pressione Enter para fechar"
