#!/usr/bin/env bash
# ==============================================================================
# test-local-prod.sh — Test local de la stack de production (image :local)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "\033[36m🧪 [GéoFoncier] Lancement du test local de la stack de production...\033[0m"

# 1. Vérification de l'image de production locale
IMAGE_TAG="geofoncier-app:local"
if [ -z "$(docker image ls -q "$IMAGE_TAG")" ]; then
    echo -e "\033[33m⚠️ Image $IMAGE_TAG introuvable. Lancement du build...\033[0m"
    bash "$SCRIPT_DIR/build-prod.sh"
fi

# 2. Gestion du fichier .env.prod.local
if [ ! -f ".env.prod.local" ]; then
    if [ -f ".env.prod.example" ]; then
        echo -e "\033[33m📄 Création de .env.prod.local à partir de .env.prod.example...\033[0m"
        cp .env.prod.example .env.prod.local
        RANDOM_KEY=$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | base64 | head -c 50)
        sed -i "s/REMPLACER_PAR_CLE_SECURISEE_GENE_PAR_GENERATE_SECRETS/${RANDOM_KEY}/g" .env.prod.local
        sed -i "s/MOT_DE_PASSE_POSTGRES_TRES_FORT_ET_SECURISE/prod_test_password/g" .env.prod.local
    else
        echo -e "\033[31m❌ Erreur : .env.prod.example introuvable !\033[0m"
        exit 1
    fi
fi

# 3. Lancement de docker-compose.local.yaml
echo -e "\033[36m🐳 Démarrage de la stack avec docker-compose.local.yaml...\033[0m"
docker compose -p geofoncier-prod-test --env-file .env.prod.local -f docker-compose.local.yaml up -d

echo -e "\n\033[32m✅ Stack de test de production démarrée !\033[0m"
echo -e "   • Application (Gunicorn) : http://localhost:8000/"
echo -e "   • Healthcheck : http://localhost:8000/health/"
echo -e "   • Pour stopper : docker compose -p geofoncier-prod-test -f docker-compose.local.yaml down"
