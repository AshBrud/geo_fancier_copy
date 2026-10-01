#!/usr/bin/env bash
# ==============================================================================
# build-prod.sh — Construction de l'image Docker de production locale
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

IMAGE_TAG="geofoncier-app:local"
echo -e "\033[36m🏗️ [GéoFoncier] Construction de l'image de production : ${IMAGE_TAG}\033[0m"

NO_CACHE=""
if [[ "${1:-}" == "--no-cache" ]]; then
    echo -e "\033[33m⚡ Option --no-cache activée.\033[0m"
    NO_CACHE="--no-cache"
fi

docker build $NO_CACHE -t "$IMAGE_TAG" -f docker/Dockerfile.prod .

echo -e "\n\033[32m✅ Image ${IMAGE_TAG} construite avec succès !\033[0m"
echo -e "   Pour tester en local : ./scripts/test-local-prod.sh"
