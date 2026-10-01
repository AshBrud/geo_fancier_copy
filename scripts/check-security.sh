#!/usr/bin/env bash
# ==============================================================================
# check-security.sh — Audit de sécurité et analyse CVE avec Docker Scout
# ==============================================================================
set -euo pipefail

IMAGE="${1:-geofoncier-app:local}"

echo -e "\033[36m🛡️ [GéoFoncier] Démarrage de l'audit de sécurité sur l'image : ${IMAGE}\033[0m"

if ! docker scout version >/dev/null 2>&1; then
    echo -e "\033[33m⚠️ Docker Scout n'est pas installé ou activé dans ce client Docker.\033[0m"
    echo -e "   Pour l'activer : visitez https://docs.docker.com/scout/"
    exit 0
fi

echo -e "\n\033[36m📊 [1/2] Vue synthétique (Quickview)...\033[0m"
docker scout quickview "$IMAGE"

echo -e "\n\033[36m🔍 [2/2] Détection des vulnérabilités critiques et élevées (CVEs)...\033[0m"
docker scout cves --only-severity critical,high "$IMAGE"

echo -e "\n\033[32m✅ Audit de sécurité terminé.\033[0m"
