# ==============================================================================
# generate-secrets.ps1 - Generateur de cles cryptographiques pour Django
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function New-RandomHexKey([int]$Length = 64) {
    $Bytes = New-Object byte[] ($Length / 2)
    $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $Rng.GetBytes($Bytes)
    return -join ($Bytes | ForEach-Object { "{0:x2}" -f $_ })
}

function New-DjangoSecretKey() {
    $Chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    $Key = ""
    $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $Byte = New-Object byte[] 1
    for ($i = 0; $i -lt 50; $i++) {
        $Rng.GetBytes($Byte)
        $Index = $Byte[0] % $Chars.Length
        $Key += $Chars[$Index]
    }
    return $Key
}

Write-Host "[GeoFoncier] Generation de secrets cryptographiques..." -ForegroundColor Cyan

$DjangoKey = New-DjangoSecretKey
$HexSecret = New-RandomHexKey 64
$DbPassword = New-RandomHexKey 32

Write-Host "`n1. Cle secrete Django (SECRET_KEY) :" -ForegroundColor Green
Write-Host "   $DjangoKey" -ForegroundColor White

Write-Host "`n2. Token hexadecimal (64 caracteres) :" -ForegroundColor Green
Write-Host "   $HexSecret" -ForegroundColor White

Write-Host "`n3. Mot de passe fort PostgreSQL (DB_PASSWORD) :" -ForegroundColor Green
Write-Host "   $DbPassword" -ForegroundColor White

Write-Host "`nCopiez ces valeurs dans votre fichier .env.prod ou dans l'interface Coolify UI." -ForegroundColor Gray
