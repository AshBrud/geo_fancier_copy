# ==============================================================================
# build-prod.ps1 - Construction de l'image Docker de production locale
# ==============================================================================
[CmdletBinding()]
param(
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$ImageTag = "geofoncier-app:local"
Write-Host "[GeoFoncier] Construction de l'image de production : $ImageTag" -ForegroundColor Cyan

$BuildArgs = @(
    "build",
    "-t", $ImageTag,
    "-f", "docker/Dockerfile.prod",
    "."
)

if ($NoCache) {
    Write-Host "Option --no-cache activee." -ForegroundColor Yellow
    $BuildArgs += "--no-cache"
}

docker @BuildArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nImage $ImageTag construite avec succes !" -ForegroundColor Green
    Write-Host "   Pour tester en local : ./scripts/test-local-prod.ps1" -ForegroundColor White
} else {
    Write-Error "Echec de la construction de l'image Docker !"
}
