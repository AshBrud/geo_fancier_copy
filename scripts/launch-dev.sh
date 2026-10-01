#!/usr/bin/env bash
# ==============================================================================
# launch-dev.sh — Démarrage automatisé de l'environnement de développement
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "\033[36m🚀 [GéoFoncier] Initialisation de l'environnement de développement...\033[0m"

# 1. Vérification du fichier d'environnement
if [ ! -f ".env.dev" ]; then
    if [ -f ".env.dev.example" ]; then
        echo -e "\033[33m📄 Création de .env.dev à partir de .env.dev.example...\033[0m"
        cp .env.dev.example .env.dev
    else
        echo -e "\033[31m❌ Erreur : .env.dev.example introuvable !\033[0m"
        exit 1
    fi
fi

# 2. Vérification et création du réseau Docker externe
NETWORK_NAME="geenkodev-network"
if ! docker network ls --format '{{.Name}}' | grep -Eq "^${NETWORK_NAME}\$"; then
    echo -e "\033[33m🌐 Création du réseau Docker externe '${NETWORK_NAME}'...\033[0m"
    docker network create "$NETWORK_NAME"
fi

# 3. Démarrage de la stack avec Docker Compose
echo -e "\033[36m🐳 Lancement des conteneurs via docker-compose.dev.yaml...\033[0m"
docker compose -p geofoncier-dev --env-file .env.dev -f docker-compose.dev.yaml up -d --build

echo -e "\n\033[32m✅ Stack de développement opérationnelle !\033[0m"
echo -e "   • Application : http://localhost:8010/"
echo -e "   • Healthcheck : http://localhost:8010/health/"
echo -e "   • Base PostGIS : localhost:5433 (user: postgres, db: uad_sig_db)"
echo -e "   • Logs : docker compose -p geofoncier-dev -f docker-compose.dev.yaml logs -f"
