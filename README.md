# 🌍 GéoFoncier NGOGOM_UAD

> **Application web de SIG foncier piloté par drone** (Django 5.2 + GeoDjango + PostGIS).
> Gestion territoriale, analyse d'occupation du sol et cadastre participatif appliqués au **Campus de l'Université Alioune Diop de Bambey (UAD)** et à la **Commune de Ngogom** (Sénégal).

---

## 📌 Sommaire

1. [À Propos du Projet](#-à-propos-du-projet)
2. [Prérequis Système](#-prérequis-système)
3. [Démarrage Rapide (En 2 minutes)](#-démarrage-rapide-en-2-minutes)
4. [Boîte à Outils d'Automatisation (Dossier `scripts/`)](#-boîte-à-outils-dautomatisation-dossier-scripts)
5. [Orchestration Docker Compose](#-orchestration-docker-compose)
6. [Gestion des Variables d'Environnement](#-gestion-des-variables-denvironnement)
7. [Gestionnaire de Paquets Moderne : `uv`](#-gestionnaire-de-paquets-moderne--uv)
8. [Commandes Utiles & Exploitation SIG](#-commandes-utiles--exploitation-sig)
9. [Architecture & Arborescence](#-architecture--arborescence)
10. [Documentation Complémentaire](#-documentation-complémentaire)

---

## 💡 À Propos du Projet

Issu du mémoire d'ingénieur *« Conception et mise en place d'une application basée sur les drones pour une gestion durable du domaine foncier de l'UAD »*, GéoFoncier répond à deux enjeux territoriaux majeurs :

* **Campus UAD (Bambey)** : Inventaire foncier fin (bâtiments, terrains sportifs, espaces verts, voiries), calcul automatique des taux d'occupation, chaîne de traitement photogrammétrique par drone, et **système d'aide à la décision pour les nouvelles constructions** (analyse de faisabilité et scoring multicritère sur 100).
* **Commune de Ngogom** : Délimitation des villages et des maisons (statut d'occupation), réseau routier et **module citoyen de signalement géolocalisé** d'incidents (eau, électricité, voirie) avec circuit de traitement administratif et notifications en temps réel.
* **Vision Cible (« Un lieu = un dossier »)** : Rendre la plateforme universelle. L'ajout d'un nouveau territoire (autre université, commune rurale ou zone agricole) consistera à déposer un dossier contenant un fichier `territoire.toml` et ses couches GeoJSON, sans modification de code.

---

## 🛠️ Prérequis Système

Pour travailler sur ce projet, vous devez disposer des outils suivants :

| Outil | Version Recommandée | Utilité |
|---|---|---|
| **Docker & Docker Compose** | Docker Desktop ≥ 24 / Engine ≥ 24 | **Recommandé** : Orchestration de la stack complète (App Django + PostGIS). |
| **Python** | 3.11.x | Nécessaire si vous travaillez hors conteneur (compatibilité GDAL). |
| **`uv` (Astral)** | Dernière version (`>=0.4`) | Gestionnaire de paquets et d'environnements ultra-rapide remplaçant `pip`. |
| **PostgreSQL + PostGIS** | PostgreSQL ≥ 14 + PostGIS ≥ 3 | SGBD spatial (déjà fourni automatiquement par Docker). |
| **Git** | Dernière version | Gestion de versions du code source. |

> [!TIP]
> **Pourquoi privilégier Docker ?**
> GeoDjango requiert des bibliothèques C compilées (`gdal`, `geos`, `proj`). L'utilisation de Docker élimine tous les problèmes d'installation et de compatibilité de ces bibliothèques sous Windows.

---

## 🚀 Démarrage Rapide (En 2 minutes)

La méthode standardisée pour démarrer le projet en développement local repose sur les scripts fournis :

### Sous Windows (PowerShell) :
```powershell
.\scripts\launch-dev.ps1
```

### Sous Linux / macOS (Bash) :
```bash
bash ./scripts/launch-dev.sh
```

### Ce qui est fait automatiquement :
1. Détection ou création du fichier `.env.dev` à partir de `.env.dev.example`.
2. Création du réseau Docker externe `geenkodev-network`.
3. Construction de l'image de dev avec `uv` et montage du code à chaud (live-reload).
4. Démarrage de la base spatiale PostgreSQL / PostGIS.

### 🌐 Points d'Accès :
* **Application Web** : [http://localhost:8010/](http://localhost:8010/) (redirige vers le tableau de bord)
* **Healthcheck HTTP** : [http://localhost:8010/health/](http://localhost:8010/health/)
* **Administration Django** : [http://localhost:8010/admin/](http://localhost:8010/admin/)
* **Base de données PostGIS** : `localhost:5433` (User: `postgres`, Password: `...`, Base: `uad_sig_db`)

---

## 🧰 Boîte à Outils d'Automatisation (Dossier `scripts/`)

Le dossier [`scripts/`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/scripts/) contient l'ensemble des commandes nécessaires au cycle de vie de l'application. Chaque script est strictement appairé en **PowerShell (`.ps1`)** pour Windows et en **Bash (`.sh`)** pour Linux/macOS.

| Script | Rôle & Fonctionnement Détaillé | Commande d'Exécution |
|---|---|---|
| **`launch-dev`** | **Démarrage du Dev Local**<br>• Vérifie et initialise `.env.dev` si manquant.<br>• Crée le réseau Docker `geenkodev-network`.<br>• Démarre la stack de développement avec volume monté (`./app:/app/app`) pour rechargement à chaud. | Windows : `.\scripts\launch-dev.ps1`<br>Linux : `bash ./scripts/launch-dev.sh` |
| **`build-prod`** | **Construction de l'Image de Production**<br>• Construit l'image Docker multi-stage `geofoncier-app:local` via `docker/Dockerfile.prod`.<br>• Utilise le cache `uv` et crée l'utilisateur système `geenkodev`.<br>• Accepte l'option `--no-cache`. | Windows : `.\scripts\build-prod.ps1 [-NoCache]`<br>Linux : `bash ./scripts/build-prod.sh [--no-cache]` |
| **`test-local-prod`** | **Test Local de la Production**<br>• Vérifie l'existence de l'image locale (ou lance le build).<br>• Initialise `.env.prod.local` avec des clés temporaires sécurisées.<br>• Démarre l'application sous Gunicorn sur le port `8000` avec WhiteNoise et réseau isolé. | Windows : `.\scripts\test-local-prod.ps1`<br>Linux : `bash ./scripts/test-local-prod.sh` |
| **`check-security`** | **Audit de Sécurité & CVEs**<br>• Analyse l'image `geofoncier-app:local` avec **Docker Scout**.<br>• Fournit une vue synthétique (`quickview`) et filtre les vulnérabilités de sévérité critique et élevée. | Windows : `.\scripts\check-security.ps1`<br>Linux : `bash ./scripts/check-security.sh` |
| **`generate-secrets`** | **Générateur Cryptographique**<br>• Génère une clé secrète Django aléatoire pour `SECRET_KEY`.<br>• Génère un token hexadécimal fort de 64 caractères.<br>• Génère un mot de passe robuste pour PostgreSQL (`DB_PASSWORD`). | Windows : `.\scripts\generate-secrets.ps1`<br>Linux : `bash ./scripts/generate-secrets.sh` |

---

## 🏛️ Orchestration Docker Compose

Le projet adopte la norme stricte des 3 configurations Docker Compose :

```text
┌───────────────────────────────┬───────────────────────────────┬─────────────────────────────────┐
│   docker-compose.dev.yaml     │   docker-compose.local.yaml   │ docker-compose.coolify.prod.yaml│
├───────────────────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ • Projet : geofoncier-dev     │ • Projet : geofoncier-prod-test│ • Projet : géré par Coolify v4 │
│ • Live-reload actif (volumes) │ • Image : geofoncier-app:local│ • Image de prod (multi-stage)   │
│ • Réseau : geenkodev-network  │ • Réseau isolé de test        │ • Réseau externe : coolify      │
│ • Ports : 8010 (app), 5433 (db│ • Port : 8000 (Gunicorn)      │ • Labels Traefik v3 & SSL auto  │
└───────────────────────────────┴───────────────────────────────┴─────────────────────────────────┘
```

---

## 📄 Gestion des Variables d'Environnement

Le projet sépare strictement les fichiers d'exemples versionnés des configurations réelles :

1. **Fichiers committés dans Git** :
   * **[`.env.dev.example`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/.env.dev.example)** : Configuration prête à l'emploi pour le développement local.
   * **[`.env.prod.example`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/.env.prod.example)** : Modèle de toutes les variables requises pour déployer en production.
   * **[`.env.prod.coolify`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/.env.prod.coolify)** : Fiche mémo pour renseigner l'interface graphique de Coolify v4.
2. **Fichiers sensibles exclus par [`.gitignore`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/.gitignore)** :
   * `.env.dev`, `.env.prod.local`, `.env`.
   * **Ne committez jamais vos véritables mots de passe ou clés privées dans Git.**

---

## ⚡ Gestionnaire de Paquets Moderne : `uv`

Le projet utilise **`uv`** (Astral) à la place de `pip` pour des installations 10× à 100× plus rapides et une reproductibilité absolue via [`pyproject.toml`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/pyproject.toml).

### Commandes fréquentes avec `uv` (si travail en local) :
```bash
# Créer l'environnement virtuel local
uv venv

# Installer les dépendances du projet
uv sync

# Ajouter une nouvelle dépendance
uv add nom_paquet

# Exécuter une commande Django dans l'environnement virtuel
uv run python app/manage.py migrate
```

---

## 💻 Commandes Utiles & Exploitation SIG

### 1. Créer un Compte Administrateur Django
Dans le conteneur de dev :
```bash
docker exec -it geofoncier-dev-app python app/manage.py createsuperuser
```

### 2. Appliquer les Migrations de Base de Données
```bash
docker exec -it geofoncier-dev-app python app/manage.py migrate
```

### 3. Contrôler les Migrations (Règle d'or avant de commit)
```bash
docker exec -it geofoncier-dev-app python app/manage.py makemigrations --check
```

### 4. Importer des Couches Cartographiques (GeoJSON / Shapefile)
Les commandes d'importation sont idempotentes et supportent l'option `--dry-run` pour tester avant d'écrire en base :
```bash
# Valider sans écrire en base
docker exec -it geofoncier-dev-app python app/manage.py import_espaces_sig donnees/espaces_campus.geojson --dry-run

# Import réel
docker exec -it geofoncier-dev-app python app/manage.py import_espaces_sig donnees/espaces_campus.geojson
docker exec -it geofoncier-dev-app python app/manage.py import_batiments_sig donnees/batiments_campus.geojson
```

### 5. Exporter une Carte HTML Autonome (Folium)
```bash
docker exec -it geofoncier-dev-app python app/manage.py export_carte_folium
```
Le fichier autonome est généré dans `donnees/carte_campus_folium.html`.

---

## 📂 Architecture & Arborescence

```text
geo_fancier_copy/
├── app/                                 # 📦 Cœur applicatif Django
│   ├── accounts/                        # Utilisateurs personnalisés (CustomUser) et rôles
│   ├── commune/                         # SIG communal de Ngogom (villages, maisons, signalements)
│   ├── constructions/                   # Aide à la décision & faisabilité des nouvelles constructions
│   ├── dashboard/                       # Tableaux de bord synthétiques et graphiques Chart.js
│   ├── donnees/                         # Modèles de fichiers GeoJSON pour les tests et imports
│   ├── drones/                          # Missions de vol, traitement photogrammétrique, tuiles XYZ
│   ├── foncier/                         # Inventaire foncier du campus UAD (espaces, bâtiments, voiries)
│   ├── navigation/                      # Moteur de recherche spatiale
│   ├── pdu/                             # Statistiques d'urbanisme (Plan Directeur d'Urbanisme)
│   ├── static/                          # Design System modulaire (geofoncier.css, geofoncier.js, modules)
│   ├── templates/                       # Gabarits HTML Bootstrap 5 (base.html, cartes, formulaires)
│   ├── config/                          # Configuration Django (settings.py, urls.py, wsgi.py)
│   └── manage.py                        # Point d'entrée des commandes Django
├── docker/                              # 🐳 Configuration Docker
│   ├── Dockerfile.dev                   # Image de développement local avec uv
│   ├── Dockerfile.prod                  # Image de production multi-stage sécurisée (user geenkodev)
│   └── entrypoint.sh                    # Point d'entrée appliquant migrations et collectstatic
├── scripts/                             # 🚀 Outillage d'automatisation (.ps1 et .sh)
├── docs/                                # 📚 Documentation technique détaillée et règles d'agents
├── pyproject.toml                       # ⚡ Configuration des dépendances uv
├── docker-compose.dev.yaml              # 🛠️ Stack dev locale
├── docker-compose.local.yaml            # 🧪 Stack de validation prod locale
├── docker-compose.coolify.prod.yaml     # 🌐 Stack de déploiement officiel Coolify v4
├── .env.dev.example                     # 📄 Gabarit d'environnement dev
├── .env.prod.example                    # 📄 Gabarit d'environnement prod
├── .env.prod.coolify                    # 📄 Mémo pour configuration Coolify UI
└── .gitignore                           # 🛡️ Protection des secrets et données locales
```

---

## 📚 Documentation Complémentaire

Pour approfondir les règles métier et les spécificités du projet :
* **[Vision Stratégique & Modèle Open-Core](docs/vision/modele_open_core_et_territoires.md)** : Modèle d'affaires Open-Core (Netdata/Chatwoot), système de dossiers et RBAC multi-utilisateurs.
* **[Règles d'Agent — Vision Long Terme](.agents/vision-long-terme.md)** : Boussole d'architecture, système de dossiers et RBAC pour agents et développeurs.
* **[Règles d'Agent — Invariants Initiaux](.agents/vision-global-initial.md)** : Règles absolues sur les projections spatiales, calculs métriques et permissions.
* **[Prise en Main Détaillée](docs/prise_en_main.md)** : Guide d'installation étape par étape.
* **[Architecture Système](docs/architecture.md)** : Description des flux métier, du modèle spatial et des API REST.
* **[Technologies Utilisées](docs/technologies.md)** : Inventaire de toutes les briques logicielles.
* **[Territoires (« Un lieu = un dossier »)](docs/territoires.md)** : Vision cible, dette technique de lieu et feuille de route.
* **[Pipeline d'Import SIG](docs/import_sig.md)** : Documentation des formats de fichiers attendus pour les levés terrain.
* **[Standardisation Docker & Scripts](docs/rules/regle_agent_standardisation_docker_compose_scripts.md)** : Directives officielles d'orchestration GeenkoDev.
