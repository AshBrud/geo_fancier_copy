@echo off
echo ============================================
echo   GeoFoncier NGOGOM_UAD - Demarrage reseau
echo ============================================
echo.

:: Recuperation de l'adresse IP via PowerShell
for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' -or $_.InterfaceAlias -like '*WiFi*' -or $_.InterfaceAlias -like '*WLAN*' } | Select-Object -First 1).IPAddress"`) do set IP=%%a

if "%IP%"=="" (
    for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object -First 1).IPAddress"`) do set IP=%%a
)

echo  Votre adresse IP : %IP%
echo.
echo  Acces depuis ce PC      : http://localhost:8000
echo  Acces depuis telephone  : http://%IP%:8000
echo  Acces depuis autre PC   : http://%IP%:8000
echo.
echo ============================================
echo  Appuyez sur Ctrl+C pour arreter le serveur
echo ============================================
echo.

cd /d "%~dp0"
call venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
pause
