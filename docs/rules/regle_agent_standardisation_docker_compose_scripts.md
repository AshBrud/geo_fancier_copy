---
trigger: model_decision
description: Directives d'ingénierie et de standardisation Docker Compose, scripts d'automatisation (scripts/) et déploiement Coolify v4 pour les projets GeenkoDev. À consulter lors de l'initialisation ou de la conteneurisation d'un projet.
---

# 🐳 Règle Générale : Standardisation Docker Compose, Scripts Local Dev & Déploiement Coolify v4

> [!IMPORTANT]
> **Règle d'Architecture & Orchestration GeenkoDev** : Tous les projets applicatifs de l'écosystème GeenkoDev / Projet Fusion doivent adopter la structure standardisée de conteneurisation Docker, l'outillage de scripts automatisés dans `scripts/` et la triple configuration Docker Compose décrites ci-dessous.

---

## 🏛️ 1. Matrice des 3 Fichiers Docker Compose

Tout projet conteneurisé doit obligatoirement inclure 3 configurations Docker Compose distinctes à la racine :

| Fichier Compose | Usage & Environnement | Nom de Projet Docker (`-p`) | Réseaux & Ports |
| :--- | :--- | :--- | :--- |
| **`docker-compose.dev.yaml`** | Développement local rapide avec volumes montés à chaud et rechargement (live-reload). | `<projet>-dev` | Réseau externe `geenkodev-network`. Ports exposés pour le dev (`8010`, `3011`, etc.). |
| **`docker-compose.local.yaml`** | Test local de la stack de production avant déploiement cloud (images pré-construites). | `<projet>-prod-test` | Réseau bridge dédié (`<projet>-prod-network`). Base de données sur volume local isolé. |
| **`docker-compose.coolify.prod.yaml`** | Déploiement officiel en production sur serveur sous Coolify v4 et Traefik v3. | Géré par Coolify | Réseau externe `coolify`. Reverse proxy Traefik, SSL automatique et healthchecks. |

---

## 🚀 2. Standardisation du Dossier `scripts/`

Tout projet doit fournir un dossier `scripts/` à la racine contenant des scripts appairés **PowerShell (`.ps1`)** pour Windows et **Bash (`.sh`)** pour Linux/macOS :

### 📋 Liste des 5 Scripts Obligatoires :

1. **`launch-dev.ps1` / `launch-dev.sh`** :
   - Vérifie et initialise le fichier `.env.dev` à partir de `.env.dev.example` si absent.
   - S'assure que le réseau Docker externe `geenkodev-network` existe (`docker network create`).
   - Démarre la stack de dev via `docker compose -p <projet>-dev --env-file .env.dev -f docker-compose.dev.yaml up -d --build`.

2. **`build-prod.ps1` / `build-prod.sh`** :
   - Construit les images Docker de production locales (`<projet>-api:local`, `<projet>-dash:local`) avec étiquettes `:local`.
   - Option `--no-cache` via flag `[switch]$NoCache`.

3. **`test-local-prod.ps1` / `test-local-prod.sh`** :
   - Détecte `.env.prod.local` (ou fallback sur `.env.prod`).
   - Instancie la stack intégrée de production en local via `docker compose -p <projet>-prod-test --env-file $envFile -f docker-compose.local.yaml up -d`.

4. **`check-security.ps1` / `check-security.sh`** :
   - Exécute `docker scout quickview` et `docker scout cves --only-severity critical,high` sur les images locales pour détecter les vulnérabilités CVE avant déploiement.

5. **`generate-secrets.ps1` / `generate-secrets.sh`** :
   - Génère des clés cryptographiques aléatoires (64 caractères hex via `openssl rand -hex 32` ou `RNGCryptoServiceProvider`).

---

## 📄 3. Hiérarchie des Fichiers d'Environnement (`.env.*`)

1. **Fichiers de Référence Committés dans Git** :
   - `.env.dev.example` : Modèle de variables pour le développement local (`ENVIRONMENT=local`).
   - `.env.prod.example` : Modèle complet de toutes les variables requises en production.
   - `.env.prod.coolify` : Fichier de documentation des variables pour l'interface Coolify UI.
2. **Fichiers Locaux Ignorés par Git (`.gitignore`)** :
   - `.env.dev` (créé par `launch-dev.ps1`).
   - `.env.prod.local` (créé par `test-local-prod.ps1`).
   - `.env.local` (variables d'environnement locales Next.js / Node).

> [!CAUTION]
> Ne jamais committer de vrais mots de passe, tokens JWT ou clés d'API dans les fichiers `.example` ou `.coolify`.

---

## 📦 4. Normes de Build des Dockerfiles (`Dockerfile.prod`)

1. **Multi-Stage Build & Images Légeres** :
   - Python : Image `python:3.13-slim` avec gestionnaire `uv` (`uv sync --frozen --no-dev`).
   - Node.js / Next.js : Image `node:22-alpine` avec `output: "standalone"` et `pnpm@12.6.0`.
2. **Sécurité & Utilisateur Non-Privilégié** :
   - Interdiction de tourner en `root`.
   - Créer et utiliser un utilisateur système non-privilégié `geenkodev` (UID 10001 ou 1001).
3. **Healthchecks Applicatifs Obligatoires** :
   - FastAPI : Test HTTP sur `/health` via `urllib.request`.
   - Next.js : Test HTTP sur `/api/health` via `node -e "fetch(...)"`.

---

## 🌐 5. Conformité Coolify v4 & Traefik v3

1. **Préservation des IP Réseau (`X-Forwarded-For`)** :
   - Traefik v3 transmet l'IP client d'origine dans le header `X-Forwarded-For`. Les APIs FastAPI doivent obligatoirement activer `send_default_pii=True` dans Sentry/GlitchTip pour la télémétrie.
2. **Variables d'Argument au Build Next.js (`args:`)** :
   - Toutes les variables injectées au build client (`NEXT_PUBLIC_*` et `SENTRY_AUTH_TOKEN`) doivent être explicitement passées dans la section `build.args` de `docker-compose.coolify.prod.yaml`.
