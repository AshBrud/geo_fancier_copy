# ==============================================================================
# launch-dev.ps1 - Demarrage automatise de l'environnement de developpement
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "[GeoFoncier] Initialisation de l'environnement de developpement..." -ForegroundColor Cyan

# 1. Verification du fichier d'environnement
$EnvDevPath = Join-Path $ProjectRoot ".env.dev"
$EnvExamplePath = Join-Path $ProjectRoot ".env.dev.example"

if (-not (Test-Path $EnvDevPath)) {
    if (Test-Path $EnvExamplePath) {
        Write-Host "Creation de .env.dev a partir de .env.dev.example..." -ForegroundColor Yellow
        Copy-Item -Path $EnvExamplePath -Destination $EnvDevPath
    } else {
        Write-Error "Fichier .env.dev.example introuvable !"
    }
}

# 2. Verification et creation du reseau Docker externe
$NetworkName = "geenkodev-network"
$NetworkExists = docker network ls --filter "name=^${NetworkName}$" --format "{{.Name}}"
if (-not $NetworkExists) {
    Write-Host "Creation du reseau Docker externe '${NetworkName}'..." -ForegroundColor Yellow
    docker network create $NetworkName
}

# 3. Demarrage de la stack avec Docker Compose
Write-Host "Lancement des conteneurs via docker-compose.dev.yaml..." -ForegroundColor Cyan
docker compose -p geofoncier-dev --env-file .env.dev -f docker-compose.dev.yaml up -d --build

Write-Host "`nStack de developpement operationnelle !" -ForegroundColor Green
Write-Host "   - Application : http://localhost:8010/" -ForegroundColor White
Write-Host "   - Healthcheck : http://localhost:8010/health/" -ForegroundColor White
Write-Host "   - Base PostGIS : localhost:5433 (user: postgres, db: uad_sig_db)" -ForegroundColor White
Write-Host "   - Logs : docker compose -p geofoncier-dev -f docker-compose.dev.yaml logs -f" -ForegroundColor Gray
