# Atlas - Atualizador PowerShell
# Rode: powershell -ExecutionPolicy Bypass -File Atlas-atualizar.ps1

$Pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Pasta

$RepoUrl = "https://github.com/Somaisumser/Atlas-assistent"
$ZipUrl = "$RepoUrl/archive/refs/heads/main.zip"
# Pastas e arquivos que nunca podem ser apagados pela atualizacao
$Protegidos = @("venv", "backups", "codigos", "__pycache__", ".git",
                "lembretes.json", "config.json", ".atlas_state.json",
                ".last_update_hash")

function Escrever-Cabecalho {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host "       ATLAS - ATUALIZADOR" -ForegroundColor Cyan
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host ""
}

Escrever-Cabecalho

# ---------------------------------------------------------------
# Metodo 1: Git (preserva o historico e nunca sobrescreve alteracoes)
# ---------------------------------------------------------------
if (Test-Path ".git") {
    $Git = Get-Command git -ErrorAction SilentlyContinue
    if ($Git) {
        Write-Host "  Verificando atualizacoes via Git..." -ForegroundColor Yellow
        Write-Host ""

        git pull origin main
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "  ==========================================" -ForegroundColor Green
            Write-Host "       ATUALIZACAO CONCLUIDA!" -ForegroundColor Green
            Write-Host "  ==========================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "  Se houve atualizacoes, reinicie o Atlas." -ForegroundColor White
            Read-Host "Pressione Enter para fechar"
            exit 0
        }

        Write-Host ""
        Write-Host "  O Git nao conseguiu atualizar." -ForegroundColor Yellow
        Write-Host "  Motivo comum: existem alteracoes locais ainda nao commitadas." -ForegroundColor Yellow
        Write-Host "  Use 'git status' e 'git add . && git commit -m \"...\"' e tente de novo." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  As alteracoes locais NAO foram apagadas." -ForegroundColor Green
        Read-Host "Pressione Enter para fechar"
        exit 1
    }
}

# ---------------------------------------------------------------
# Metodo 2: ZIP (sem Git) - faz backup antes de sobrescrever
# ---------------------------------------------------------------
Write-Host "  Git nao encontrado. Baixando a versao mais recente..." -ForegroundColor Yellow
Write-Host ""

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ZipTemp = Join-Path $env:TEMP "atlas-update.zip"
$DirTemp = Join-Path $env:TEMP "atlas-update"

try {
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipTemp -ErrorAction Stop
} catch {
    Write-Host "  [ERRO] Falha ao baixar. Verifique sua internet." -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

if (Test-Path $DirTemp) { Remove-Item $DirTemp -Recurse -Force -ErrorAction SilentlyContinue }
try {
    Expand-Archive -Path $ZipTemp -DestinationPath $DirTemp -Force
} catch {
    Write-Host "  [ERRO] Falha ao extrair o pacote." -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

$Src = Join-Path $DirTemp "Atlas-assistent-main"
if (-not (Test-Path $Src)) {
    Write-Host "  [ERRO] Pacote invalido." -ForegroundColor Red
    Read-Host "Pressione Enter para fechar"
    exit 1
}

# Backup dos arquivos do projeto antes de qualquer sobrescrita
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Pasta "backup_local_$Stamp"
New-Item -ItemType Directory -Path $Backup -Force | Out-Null
Get-ChildItem -Path $Pasta -File -Include *.py,*.json,*.md,*.txt,*.bat,*.ps1 |
    Where-Object { $_.Name -notin @("config.json", "lembretes.json", ".atlas_state.json", ".last_update_hash") } |
    ForEach-Object { Copy-Item $_.FullName (Join-Path $Backup $_.Name) -Force }
Write-Host "  Backup dos arquivos locais salvo em: backup_local_$Stamp" -ForegroundColor Green
Write-Host ""

$copiados = 0
$preservados = @()
Get-ChildItem -Path $Src | ForEach-Object {
    $item = $_.Name
    $destino = Join-Path $Pasta $item
    if ($item -in $Protegidos -or $item.StartsWith("backup_")) { return }

    if ($item -eq "config.json" -or $item -eq "lembretes.json") { return }

    if (Test-Path $destino) {
        $local = Get-Item $destino
        if ($local.PSIsContainer) {
            Remove-Item $destino -Recurse -Force -ErrorAction SilentlyContinue
            Copy-Item $_.FullName $destino -Recurse -Force
        } else {
            # Arquivo que ja existe e foi alterado localmente: preserva
            if ($local.LastWriteTime -gt (Get-Date).AddDays(-30)) {
                $preservados += $item
                return
            }
            Copy-Item $_.FullName $destino -Force
        }
    } else {
        Copy-Item $_.FullName $destino -Recurse -Force
    }
    $copiados++
}

# Limpa o temporario
Remove-Item $DirTemp -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $ZipTemp -Force -ErrorAction SilentlyContinue

# Atualiza dependencias
if (Test-Path "venv\Scripts\pip.exe") {
    Write-Host "  Atualizando dependencias..." -ForegroundColor Yellow
    & "venv\Scripts\pip.exe" install -r requirements.txt --quiet
}

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Green
Write-Host "       ATUALIZACAO CONCLUIDA!" -ForegroundColor Green
Write-Host "  ==========================================" -ForegroundColor Green
Write-Host ""
if ($preservados.Count -gt 0) {
    Write-Host "  Arquivos locais preservados (alterados recentemente):" -ForegroundColor Yellow
    $preservados | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
    Write-Host "  As versoes novas estao no backup_local_$Stamp." -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "  Reinicie o Atlas." -ForegroundColor White
Write-Host ""
Read-Host "Pressione Enter para fechar"
