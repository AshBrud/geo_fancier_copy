# Prise en main

L'objectif : passer d'un clone du dépôt à une application qui tourne en moins
d'une heure, sous Windows (plateforme de développement actuelle).

## 1. Prérequis

| Outil | Version de référence | Remarque |
|---|---|---|
| Python | 3.11 | Le venv du projet utilise 3.11.9 |
| PostgreSQL + PostGIS | PostgreSQL 17 (Alpine `postgres:17-alpine` ou `postgis/postgis:17-3.5-alpine`), PostGIS 3.5 | Base `uad_sig_db` par défaut. Requiert le support des extensions spatiales PostGIS. |
| GDAL (wheel `osgeo`) | 3.11.x | Installé **dans le venv**, voir ci-dessous |
| FFmpeg | facultatif | Enregistrement des flux vidéo du drone |
| WebODM | facultatif | Traitement photogrammétrique (externe), en local sur `127.0.0.1:29800` |

## 2. Installation

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

`requirements.txt` est encodé en UTF-16. Si `pip` le lit mal, réenregistrez-le
en UTF-8.

**GDAL sous Windows** : `config/settings.py` cherche les DLL dans
`venv/Lib/site-packages/osgeo/` (`gdal.dll`, `geos_c.dll`). Il force aussi
`PROJ_DATA` pour éviter un conflit avec le PROJ embarqué par PostgreSQL. Si
GeoDjango ne trouve pas GDAL, vérifiez que le wheel GDAL est bien installé dans
le venv.

## 3. Base de données

```sql
CREATE DATABASE uad_sig_db;
\c uad_sig_db
CREATE EXTENSION postgis;
```

## 4. Fichier `.env` (à la racine, non versionné)

```ini
SECRET_KEY=une-cle-longue-et-aleatoire
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=uad_sig_db
DB_USER=postgres
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432
```

## 5. Premier lancement

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

- Accès local : <http://localhost:8000> (redirige vers `/dashboard/`).
- Accès depuis un téléphone sur le même réseau : `runserver_reseau.bat` affiche
  l'IP et écoute sur `0.0.0.0:8000`.
- Administration Django : `/admin/`.

## 6. Charger des données

La base est vide après l'installation. Dans l'ordre :

1. **Limite du territoire** : `Campus` (via l'admin ou la carte) ou `Commune`.
2. **Couches SIG** : commandes `import_*_sig` (voir [import_sig.md](import_sig.md)).
   Des modèles de fichiers se trouvent dans `donnees/`.
3. **Orthophoto** :
   - campus : module Drones → Mission → import du GeoTIFF ;
   - commune : `manage.py importer_orthophoto "<lien public WebODM>"`.

## 7. Commandes de gestion

| Commande | App | Rôle |
|---|---|---|
| `import_espaces_sig`, `import_batiments_sig`, `import_terrains_sig`, `import_espaces_verts_sig`, `import_voiries_sig`, `import_points_interet_sig` | foncier | Import GeoJSON/Shapefile → PostGIS (`--dry-run`, `--source-crs`) |
| `export_carte_folium` | foncier | Carte HTML autonome dans `donnees/` |
| `importer_orthophoto` | commune | WebODM → GeoTIFF → emprise réelle → tuiles XYZ locales |

## 8. Repères dans le code

| Besoin | Où regarder |
|---|---|
| Routage global | `config/urls.py` |
| Réglages (BD, GDAL, sessions de 30 min, e-mail console) | `config/settings.py` |
| Gabarit commun, menu, notifications | `templates/base.html`, `commune/context_processors.py` |
| Carte Leaflet partagée | `static/js/geofoncier.js` (`map.js`, `layers.js`), `templates/cartographie/map.html` |
| Rôles et permissions | `accounts/models.py` (propriétés `can_*`) |
| API GeoJSON | `foncier/api_urls.py`, `foncier/api_views.py`, `foncier/serializers.py` |

## 9. Pièges connus

- Les sessions expirent après **30 min d'inactivité** (`SESSION_COOKIE_AGE`).
- Les e-mails (réinitialisation de mot de passe) s'affichent **dans la console**
  en développement.
- `media/` n'est pas versionné : les orthophotos, tuiles et photos ne se
  transmettent pas par Git.
- Les fichiers `runserver-800x.*` à la racine sont des journaux locaux et ne
  font pas partie du code.
