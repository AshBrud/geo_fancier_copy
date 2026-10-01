# ==============================================================================
# test-local-prod.ps1 - Test local de la stack de production (image :local)
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "[GeoFoncier] Lancement du test local de la stack de production..." -ForegroundColor Cyan

# 1. Verification de l'image de production locale
$ImageTag = "geofoncier-app:local"
$ImageExists = docker image ls -q $ImageTag
if (-not $ImageExists) {
    Write-Host "Image $ImageTag introuvable. Lancement du build..." -ForegroundColor Yellow
    & "$PSScriptRoot/build-prod.ps1"
}

# 2. Gestion du fichier .env.prod.local
$EnvProdLocal = Join-Path $ProjectRoot ".env.prod.local"
$EnvProdExample = Join-Path $ProjectRoot ".env.prod.example"

if (-not (Test-Path $EnvProdLocal)) {
    if (Test-Path $EnvProdExample) {
        Write-Host "Creation de .env.prod.local a partir de .env.prod.example..." -ForegroundColor Yellow
        Copy-Item -Path $EnvProdExample -Destination $EnvProdLocal
        # Generer une cle temporaire pour le test local
        $RandomKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 50 | ForEach-Object {[char]$_})
        (Get-Content $EnvProdLocal) -replace "REMPLACER_PAR_CLE_SECURISEE_GENE_PAR_GENERATE_SECRETS", $RandomKey | Set-Content $EnvProdLocal
        (Get-Content $EnvProdLocal) -replace "MOT_DE_PASSE_POSTGRES_TRES_FORT_ET_SECURISE", "prod_test_password" | Set-Content $EnvProdLocal
    } else {
        Write-Error "Fichier .env.prod.example introuvable !"
    }
}

# 3. Lancement de docker-compose.local.yaml
Write-Host "Demarrage de la stack avec docker-compose.local.yaml..." -ForegroundColor Cyan
docker compose -p geofoncier-prod-test --env-file .env.prod.local -f docker-compose.local.yaml up -d

Write-Host "`nStack de test de production demarree !" -ForegroundColor Green
Write-Host "   - Application (Gunicorn) : http://localhost:8000/" -ForegroundColor White
Write-Host "   - Healthcheck : http://localhost:8000/health/" -ForegroundColor White
Write-Host "   - Pour stopper : docker compose -p geofoncier-prod-test -f docker-compose.local.yaml down" -ForegroundColor Gray
