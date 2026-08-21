# Jarvis - Atualizador PowerShell
# Rode: powershell -ExecutionPolicy Bypass -File atualizar.ps1

$Pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Pasta

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "       JARVIS - ATUALIZADOR" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".git")) {
    Write-Host "  [ERRO] Esta pasta nao e um repositorio Jarvis." -ForegroundColor Red
    Write-Host "  Execute 'Instalar Jarvis.bat' primeiro." -ForegroundColor Yellow
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host "  Verificando atualizacoes..." -ForegroundColor Yellow
Write-Host ""

git pull origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Green
    Write-Host "       ATUALIZACAO CONCLUIDA!" -ForegroundColor Green
    Write-Host "  ==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Se houve atualizacoes, reinicie o Jarvis." -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "  [ERRO] Falha ao atualizar." -ForegroundColor Red
    Write-Host "  Verifique sua conexao com a internet." -ForegroundColor Yellow
}

Read-Host "Pressione Enter para fechar"
