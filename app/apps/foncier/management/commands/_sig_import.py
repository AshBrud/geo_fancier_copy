import json

from django.contrib.gis.geos import (
    GEOSGeometry, MultiLineString, MultiPolygon, LineString, Point, Polygon,
)
from django.core.management.base import CommandError


TARGET_SRID = 4326


def read_layer(path, source_crs=None, layer=None):
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise CommandError(
            "GeoPandas n'est pas installe. Installez-le avec: "
            ".\\venv\\Scripts\\pip install geopandas folium"
        ) from exc

    try:
        gdf = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    except Exception as exc:
        raise CommandError(f"Impossible de lire le fichier SIG: {path}. Detail: {exc}") from exc

    if gdf.empty:
        raise CommandError("Le fichier SIG ne contient aucune entite.")

    if gdf.crs is None:
        if not source_crs:
            raise CommandError(
                "Le fichier n'a pas de CRS. Ajoutez --source-crs EPSG:xxxx "
                "ou corrigez le fichier avant l'import."
            )
        gdf = gdf.set_crs(source_crs)

    return gdf.to_crs(epsg=TARGET_SRID)


def first_existing(row, candidates, default=""):
    for name in candidates:
        if name in row and row[name] not in (None, ""):
            value = row[name]
            if hasattr(value, "item"):
                value = value.item()
            return str(value).strip()
    return default


def optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_type_espace(value):
    normalized = (value or "").strip().lower()
    aliases = {
        "libre": "libre",
        "espace libre": "libre",
        "free": "libre",
        "occupe": "occupe",
        "occupee": "occupe",
        "occupee": "occupe",
        "bati": "occupe",
        "batiment": "occupe",
        "reserve": "reserve",
        "reservee": "reserve",
        "reservee": "reserve",
        "route": "route",
        "voie": "route",
        "voirie": "route",
    }
    return aliases.get(normalized, normalized)


def clamp_taux_occupation(value):
    value = optional_float(value) or 60.0
    return min(100.0, max(1.0, value))


def geometry_to_multipolygon(shapely_geom):
    if shapely_geom is None or shapely_geom.is_empty:
        return None

    if not shapely_geom.is_valid:
        shapely_geom = shapely_geom.buffer(0)

    geojson = json.dumps(shapely_geom.__geo_interface__)
    geos_geom = GEOSGeometry(geojson, srid=TARGET_SRID)

    if isinstance(geos_geom, Polygon):
        return MultiPolygon(geos_geom, srid=TARGET_SRID)
    if isinstance(geos_geom, MultiPolygon):
        geos_geom.srid = TARGET_SRID
        return geos_geom

    return None


def geometry_to_multilinestring(shapely_geom):
    if shapely_geom is None or shapely_geom.is_empty:
        return None

    if not shapely_geom.is_valid:
        shapely_geom = shapely_geom.buffer(0)

    geojson = json.dumps(shapely_geom.__geo_interface__)
    geos_geom = GEOSGeometry(geojson, srid=TARGET_SRID)

    if isinstance(geos_geom, LineString):
        return MultiLineString(geos_geom, srid=TARGET_SRID)
    if isinstance(geos_geom, MultiLineString):
        geos_geom.srid = TARGET_SRID
        return geos_geom

    return None


def geometry_to_point(shapely_geom):
    if shapely_geom is None or shapely_geom.is_empty:
        return None

    geojson = json.dumps(shapely_geom.__geo_interface__)
    geos_geom = GEOSGeometry(geojson, srid=TARGET_SRID)

    if isinstance(geos_geom, Point):
        geos_geom.srid = TARGET_SRID
        return geos_geom

    return None


def sync_batiments(path, source_crs=None, dry_run=False):
    """
    Importe/synchronise des batiments depuis un fichier SIG (GeoJSON/Shapefile).
    Logique partagee entre la commande CLI `import_batiments_sig` et la vue web
    d'import. Retourne un dict {created, updated, skipped, errors}.
    """
    from foncier.models import Batiment, FonctionBatiment

    gdf = read_layer(path, source_crs=source_crs)

    created = 0
    updated = 0
    skipped = 0
    errors = []

    for index, row in gdf.iterrows():
        code = first_existing(row, ["code", "CODE", "fid", "FID", "id", "ID"])
        nom = first_existing(row, ["nom", "NOM", "name", "NAME", "libelle"], code)
        fonction_nom = first_existing(
            row, ["fonction", "FONCTION", "usage", "USAGE", "type", "TYPE"], ""
        )
        description = first_existing(row, ["description", "DESCRIPTION", "desc"], "")
        etages = optional_int(first_existing(row, ["etages", "ETAGES", "niveaux", "NIVEAUX"], "1")) or 1
        annee_construction = optional_int(
            first_existing(row, ["annee_construction", "ANNEE", "annee"], "")
        )

        if not code:
            skipped += 1
            errors.append(f"Ligne {index}: ignoree, code manquant.")
            continue

        geom = geometry_to_multipolygon(row.geometry)
        if geom is None:
            skipped += 1
            errors.append(f"Ligne {index} ({code}): geometrie polygonale invalide.")
            continue

        if dry_run:
            if Batiment.objects.filter(code=code).exists():
                updated += 1
            else:
                created += 1
            continue

        fonction = None
        if fonction_nom:
            fonction, _created = FonctionBatiment.objects.get_or_create(nom=fonction_nom)

        _obj, was_created = Batiment.objects.update_or_create(
            code=code,
            defaults={
                "nom": nom or code,
                "fonction": fonction,
                "etages": etages,
                "annee_construction": annee_construction,
                "description": description,
                "est_actif": True,
                "geometrie": geom,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}
