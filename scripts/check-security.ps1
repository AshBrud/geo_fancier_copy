# ==============================================================================
# check-security.ps1 - Audit de securite et analyse CVE avec Docker Scout
# ==============================================================================
[CmdletBinding()]
param(
    [string]$Image = "geofoncier-app:local"
)

$ErrorActionPreference = "Stop"

Write-Host "[GeoFoncier] Demarrage de l'audit de securite sur l'image : $Image" -ForegroundColor Cyan

# Verifier si Docker Scout est disponible
$ScoutAvailable = docker scout version 2>$null
if (-not $ScoutAvailable) {
    Write-Host "Docker Scout n'est pas installe ou active dans ce client Docker." -ForegroundColor Yellow
    Write-Host "Pour l'activer : visitez https://docs.docker.com/scout/" -ForegroundColor Gray
    exit 0
}

Write-Host "`n[1/2] Vue synthetique (Quickview)..." -ForegroundColor Cyan
docker scout quickview $Image

Write-Host "`n[2/2] Detection des vulnerabilites critiques et elevees (CVEs)..." -ForegroundColor Cyan
docker scout cves --only-severity critical,high $Image

Write-Host "`nAudit de securite termine." -ForegroundColor Green
