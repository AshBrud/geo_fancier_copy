import os
import shutil
from django.conf import settings


def extraire_metadata_geotiff(filepath):
    """Extrait emprise, résolution, dimensions et CRS depuis un fichier GeoTIFF."""
    try:
        from osgeo import gdal, osr
        from django.contrib.gis.geos import Polygon, LinearRing

        ds = gdal.Open(filepath)
        if ds is None:
            return {}

        gt = ds.GetGeoTransform()
        width = ds.RasterXSize
        height = ds.RasterYSize

        minx = gt[0]
        maxy = gt[3]
        maxx = minx + width * gt[1]
        miny = maxy + height * gt[5]

        res_x = abs(gt[1])

        src_srs = osr.SpatialReference()
        src_srs.ImportFromWkt(ds.GetProjection())
        tgt_srs = osr.SpatialReference()
        tgt_srs.ImportFromEPSG(4326)

        if src_srs.IsGeographic():
            emprise = Polygon.from_bbox((minx, miny, maxx, maxy))
            res_cm = res_x * 111320 * 100
        else:
            transform = osr.CoordinateTransformation(src_srs, tgt_srs)
            corners = [
                transform.TransformPoint(minx, miny),
                transform.TransformPoint(maxx, miny),
                transform.TransformPoint(maxx, maxy),
                transform.TransformPoint(minx, maxy),
                transform.TransformPoint(minx, miny),
            ]
            ring = LinearRing([(c[1], c[0]) for c in corners])
            emprise = Polygon(ring, srid=4326)
            res_cm = res_x * 100

        proj_desc = ''
        if src_srs.GetAttrValue('PROJCS'):
            proj_desc = src_srs.GetAttrValue('PROJCS')
        elif src_srs.GetAttrValue('GEOGCS'):
            proj_desc = src_srs.GetAttrValue('GEOGCS')

        ds = None
        return {
            'emprise': emprise,
            'resolution': round(res_cm, 4),
            'largeur_px': width,
            'hauteur_px': height,
            'systeme_proj': proj_desc[:200],
        }
    except Exception:
        return {}


def generer_tuiles_locales(ortho):
    """
    Génère une pyramide de tuiles XYZ à partir du GeoTIFF de l'orthophoto et les
    stocke dans MEDIA_ROOT/tiles/. Rend l'affichage sur la carte indépendant de WebODM.
    """
    import subprocess
    import sys

    dossier = f'ortho_{ortho.pk}'
    sortie = os.path.join(settings.MEDIA_ROOT, 'tiles', dossier)
    if os.path.isdir(sortie):
        shutil.rmtree(sortie)

    gdal2tiles = (
        shutil.which('gdal2tiles.py')
        or shutil.which('gdal2tiles')
        or os.path.join(os.path.dirname(sys.executable), 'Scripts', 'gdal2tiles.py')
        or os.path.join(os.path.dirname(sys.executable), 'gdal2tiles.py')
    )

    cmd = [sys.executable, gdal2tiles, '-p', 'mercator', '-z', '14-21', '-w', 'none', ortho.fichier.path, sortie]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if res.returncode != 0:
        raise RuntimeError(f"Échec de gdal2tiles ({res.returncode}): {res.stderr[:300]}")

    ortho.tiles_url = f"{settings.MEDIA_URL}tiles/{dossier}/{{z}}/{{x}}/{{y}}.png"
    ortho.tuiles_locales = True
    ortho.save(update_fields=['tiles_url', 'tuiles_locales'])
