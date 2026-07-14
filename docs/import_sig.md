# Pipeline SIG: GeoPandas vers Django/PostGIS

Ce projet peut suivre ce flux:

1. Collecte terrain en Shapefile ou GeoJSON.
2. Nettoyage/reprojection avec GeoPandas.
3. Import dans PostGIS via les modeles Django `Espace` et `Batiment`.
4. Affichage dans la carte Leaflet via `/api/espaces/` et `/api/batiments/`.

## Dependances

Ajouter ces dependances si elles ne sont pas encore presentes:

```txt
geopandas
folium
```

Puis installer:

```powershell
.\venv\Scripts\pip install geopandas folium
```

## Dossier conseille

Placer les donnees sources dans `donnees/`, par exemple:

```text
donnees/
  espaces_campus.geojson
  batiments_campus.geojson
  shapefiles/
```

## Colonnes attendues pour les espaces

La commande accepte plusieurs variantes de noms de colonnes.

Champs principaux:

```text
code              obligatoire, identifiant unique
nom               recommande
type_espace        libre, occupe, reserve, route
usage             optionnel
description       optionnel
taux_occupation   optionnel, 60 par defaut
geometry          obligatoire, Polygon ou MultiPolygon
```

Alias reconnus:

```text
code: code, CODE, id, ID
nom: nom, NOM, name, NAME, libelle
type_espace: type_espace, TYPE_ESPACE, type, TYPE, statut
taux_occupation: taux_occupation, TAUX_OCCUPATION, taux, TAUX
```

Validation sans ecriture:

```powershell
.\venv\Scripts\python.exe manage.py import_espaces_sig donnees\espaces_campus.geojson --dry-run
```

Import reel:

```powershell
.\venv\Scripts\python.exe manage.py import_espaces_sig donnees\espaces_campus.geojson
```

Si le fichier n'a pas de projection:

```powershell
.\venv\Scripts\python.exe manage.py import_espaces_sig donnees\espaces_campus.shp --source-crs EPSG:32628
```

## Colonnes attendues pour les batiments

```text
code                  obligatoire, identifiant unique
nom                   recommande
fonction              recommande
etages                optionnel, 1 par defaut
annee_construction    optionnel
description           optionnel
geometry              obligatoire, Polygon ou MultiPolygon
```

Validation:

```powershell
.\venv\Scripts\python.exe manage.py import_batiments_sig donnees\batiments_campus.geojson --dry-run
```

Import:

```powershell
.\venv\Scripts\python.exe manage.py import_batiments_sig donnees\batiments_campus.geojson
```

## Notes importantes

- Les fichiers sont reprojetes automatiquement en `EPSG:4326` pour la carte web.
- Les surfaces sont recalculees par les methodes `save()` des modeles avec `EPSG:32628`.
- Les objets existants sont mis a jour par leur `code`; un meme code ne cree pas de doublon.
- Pour une carte HTML hors Django, Folium reste utile pour tester rapidement un GeoJSON nettoye.

## Export rapide avec Folium

Apres import, generer une carte HTML autonome depuis la base:

```powershell
.\venv\Scripts\python.exe manage.py export_carte_folium
```

Le fichier sera cree ici:

```text
donnees/carte_campus_folium.html
```
