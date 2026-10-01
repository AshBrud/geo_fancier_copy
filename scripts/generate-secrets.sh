#!/usr/bin/env bash
# ==============================================================================
# generate-secrets.sh — Générateur de clés cryptographiques sécurisées pour Django
# ==============================================================================
set -euo pipefail

echo -e "\033[36m🔐 [GéoFoncier] Génération de secrets cryptographiques...\033[0m"

DJANGO_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 40)
HEX_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
DB_PASSWORD=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")

echo -e "\n\033[32m1. Clé secrète Django (SECRET_KEY) :\033[0m"
echo -e "   $DJANGO_KEY"

echo -e "\n\033[32m2. Token cryptographique hexadécimal (64 caractères) :\033[0m"
echo -e "   $HEX_SECRET"

echo -e "\n\033[32m3. Mot de passe fort pour PostgreSQL (DB_PASSWORD) :\033[0m"
echo -e "   $DB_PASSWORD"

echo -e "\n\033[90m💡 Copiez ces valeurs dans votre fichier .env.prod ou dans l'interface Coolify UI.\033[0m"
