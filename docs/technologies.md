# Technologies utilisées

Ce document liste chaque technologie du projet, son rôle et l'endroit où elle
intervient. Les versions viennent de `requirements.txt` et des liens CDN des
templates.

## 1. Vue d'ensemble par couche

```text
┌──────────── Acquisition ────────────┐   ┌──────────── Traitement ────────────┐
│ Drone (photos, vidéo RTSP)          │──▶│ WebODM (photogrammétrie, externe)  │
│ Terrain : QGIS → GeoJSON/Shapefile  │   │ GDAL / gdal2tiles, GeoPandas, FFmpeg│
└─────────────────────────────────────┘   └──────────────────┬─────────────────┘
                                                             ▼
┌──────────── Serveur ────────────────────────────────────────────────────────┐
│ Python 3.11 · Django 5.2 · GeoDjango · DRF + rest_framework_gis             │
│ PostgreSQL + PostGIS · media/ (GeoTIFF, tuiles XYZ, photos, vidéos)         │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           ▼
┌──────────── Navigateur ─────────────────────────────────────────────────────┐
│ Templates Django · Bootstrap 5 · Leaflet + Leaflet.draw · Chart.js · hls.js │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Back-end

| Technologie | Version | Rôle dans le projet | Où |
|---|---|---|---|
| **Python** | 3.11 | Langage du serveur et des scripts | `venv/` |
| **Django** | 5.2.15 | Framework web : modèles, vues, templates, administration, authentification | toutes les apps |
| **GeoDjango** (`django.contrib.gis`) | inclus dans Django | Champs géométriques (`MultiPolygonField`, `PointField`…), requêtes spatiales (`intersects`, `contains`), reprojection (`transform`) | `*/models.py` |
| **Django REST Framework** | 3.17 | API JSON, authentification par session, `IsAuthenticated` par défaut | `foncier/api_views.py` |
| **djangorestframework-gis** | 1.2 | Sérialisation GeoJSON pour la carte | `foncier/serializers.py` |
| **django-filter** | 25.2 | Filtrage des listes et de l'API | `REST_FRAMEWORK` dans `config/settings.py` |
| **django-crispy-forms** + **crispy-bootstrap5** | 2.6 / 2026.3 | Mise en forme Bootstrap des formulaires | templates de formulaires |
| **django-environ** | 0.13 | Lecture du fichier `.env` (secrets, base de données) | `config/settings.py` |
| **psycopg2-binary** | 2.9 | Pilote PostgreSQL | — |
| **Pillow** | 12.2 | Images (`ImageField` : photos drone, profils, signalements) | modèles |

## 3. Base de données et géospatial

| Technologie | Rôle | Remarques |
|---|---|---|
| **PostgreSQL** | Base de données relationnelle | Base `uad_sig_db` par défaut |
| **PostGIS** | Extension spatiale : stockage et calculs géométriques | Requise par GeoDjango |
| **GDAL / OGR** | 3.11.4 (wheel `osgeo`). Lit les GeoTIFF, en extrait les métadonnées, génère les tuiles (`gdal2tiles`) | DLL chargées depuis `venv/Lib/site-packages/osgeo` (voir `config/settings.py`) |
| **GEOS** | Opérations géométriques (union, intersection, aire) | Fourni avec le wheel GDAL |
| **PROJ / pyproj** | 3.7. Changements de projection | `PROJ_DATA` forcé pour éviter le PROJ de PostgreSQL |
| **Shapely** | 2.1. Géométries côté Python, pendant les imports | `foncier/management/commands/_sig_import.py` |
| **GeoPandas** | Lecture et nettoyage des GeoJSON et Shapefile, reprojection avant import | commandes `import_*_sig` |
| **NumPy** | Calcul de l'emprise réelle d'une orthophoto (canal alpha) | `commune/.../importer_orthophoto.py` |
| **Folium** | Export d'une carte HTML autonome | `export_carte_folium` |

**Systèmes de coordonnées**

| Code EPSG | Usage |
|---|---|
| **4326** (WGS 84) | Stockage de toutes les géométries, affichage Leaflet |
| **32628** (UTM 28N) | Calcul des surfaces et longueurs en mètres (ouest du Sénégal). Voir [territoires.md](territoires.md) pour l'est du pays (32629) |

## 4. Drone et traitement d'images

| Technologie | Rôle | Où |
|---|---|---|
| **WebODM** (OpenDroneMap) | Photogrammétrie : photos → orthophoto GeoTIFF. Outil **externe**, en local sur `127.0.0.1:29800` | lu par `importer_orthophoto` |
| **gdal2tiles** | Découpe du GeoTIFF en tuiles XYZ, servies depuis `media/tiles/` | `drones/views.py`, `importer_orthophoto` |
| **FFmpeg** | Enregistrement sur le serveur du flux vidéo RTSP du drone | `drones/views.py` (lancé par `subprocess`) |
| **MediaMTX** | Serveur de flux : convertit le RTSP du drone en HLS / WebRTC (WHEP) pour le navigateur | page `drones:perspectives` |

FFmpeg et MediaMTX ne servent qu'à la vidéo en direct. Le reste de
l'application fonctionne sans eux.

## 5. Front-end

Pas de framework SPA ni d'outil de build. Les bibliothèques sont chargées par CDN
dans les templates.

| Bibliothèque | Version | Rôle | Où |
|---|---|---|---|
| **Bootstrap** | 5.3.3 | Mise en page, composants, responsive (usage sur téléphone) | `templates/base.html` |
| **Bootstrap Icons** | 1.11.3 | Icônes (y compris celles des catégories de signalement) | partout |
| **Leaflet** | 1.9.4 | Carte interactive | `static/js/uad_sig.js`, cartes |
| **Leaflet.draw** | 1.0.4 | Dessin et modification de polygones dans les formulaires | `templates/foncier/*_form.html`, `templates/commune/form.html` |
| **Chart.js** | 4.4.3 | Graphiques des tableaux de bord et statistiques | `templates/dashboard/`, `templates/pdu/statistiques.html` |
| **hls.js** | 1.5.13 | Lecture du flux vidéo HLS dans le navigateur | `templates/drones/perspectives.html` |
| **Cropper.js** | 1.6.2 | Recadrage de la photo de profil | `templates/accounts/profile.html` |
| **Google Fonts** | Poppins, Roboto | Typographie | `templates/base.html` |
| JS maison | — | Initialisation commune des cartes, fonds de plan, couches | `static/js/uad_sig.js` |
| CSS maison | — | Charte graphique | `static/css/uad_sig.css` |

**Fonds de carte**

| Fond | Source |
|---|---|
| Plan | OpenStreetMap (`tile.openstreetmap.org`) |
| Satellite | Esri World Imagery (`server.arcgisonline.com`) |
| Orthophotos drone | Tuiles XYZ locales (`media/tiles/…`) |

Les fonds OSM et Esri, les CDN et Google Fonts ont besoin d'Internet. Hors
connexion, seules les orthophotos locales restent affichées.

## 6. Outils de développement et d'exploitation

| Outil | Rôle |
|---|---|
| **venv** | Environnement Python isolé (contient aussi GDAL) |
| **Git / GitHub** | Gestion des versions (`media/`, `.env` et `venv/` sont exclus) |
| **QGIS** (conseillé) | Préparation et contrôle des couches avant import |
| `runserver_reseau.bat` | Lance le serveur sur le réseau local pour un accès depuis un téléphone |
| Serveur de développement Django | Seul mode de déploiement actuel. Pas encore de configuration de production (Gunicorn/Nginx, SMTP) |

## 7. Points d'attention

- **ReportLab** (4.5) figure dans `requirements.txt` mais n'est utilisé nulle
  part dans le code. C'est une dépendance prévue pour des exports PDF ou à
  retirer.
- **GeoPandas** et **Folium** sont listés sans version fixée. Fixez-la pour que
  l'installation soit reproductible.
- `requirements.txt` est encodé en **UTF-16**, ce qui peut gêner `pip`.
  Réenregistrez-le en UTF-8.
- GDAL est chargé avec des **chemins Windows** (`gdal.dll`, `geos_c.dll`). Un
  déploiement Linux demandera d'adapter `GDAL_LIBRARY_PATH` / `GEOS_LIBRARY_PATH`
  dans `config/settings.py`.
