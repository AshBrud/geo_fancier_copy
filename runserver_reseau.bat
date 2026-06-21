@echo off
echo ============================================
echo   GeoFoncier UAD - Demarrage reseau
echo ============================================
echo.
echo Recuperation de l'adresse IP Wi-Fi...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "Wi-Fi" /a ^| findstr "IPv4"') do set IP=%%a
set IP=%IP: =%

echo.
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
