"""
Importe une orthophoto WebODM dans la cartographie communale.

    python manage.py importer_orthophoto "http://127.0.0.1:29800/public/project/<id>/map/?t=orthophoto"

Étapes (chaîne de production reproductible, documentable dans le mémoire) :
  1. lecture du lien WebODM → identification de la tâche de traitement ;
  2. téléchargement du GeoTIFF (orthophoto.tif) ;
  3. calcul de l'emprise RÉELLE couverte par l'image (canal alpha) : une
     partie de polygone par zone survolée, et non le rectangle englobant ;
  4. génération d'une pyramide de tuiles XYZ locales (gdal2tiles) servies par
     Django : la carte reste consultable sans WebODM et depuis un téléphone.
"""
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.core.management.base import BaseCommand, CommandError

from habitations.models import UTM_SRID, OrthophotoCommune

TAILLE_ANALYSE = 1500   # largeur (px) de l'image réduite utilisée pour détecter les zones
SIMPLIFICATION_M = 1.0  # tolérance de simplification du contour (m)
ZONE_MIN_M2 = 2000      # ignore les îlots de pixels isolés
FUSION_M = 15           # deux morceaux à moins de 2 × 15 m appartiennent à la même zone survolée


class Command(BaseCommand):
    help = "Importe une orthophoto WebODM (lien public) en tuiles locales pour la carte communale."

    def add_arguments(self, parser):
        parser.add_argument('lien', help="Lien public WebODM (…/public/project/<id>/map/) ou URL d'une tâche")
        parser.add_argument('--nom', default='', help="Nom de l'orthophoto (défaut : titre du projet WebODM)")
        parser.add_argument('--zoom-max', type=int, default=21, help='Niveau de zoom maximal des tuiles (défaut 21)')
        parser.add_argument('--reutiliser', action='store_true', help='Ne pas re-télécharger un GeoTIFF déjà présent')
        parser.add_argument('--emprise-seule', action='store_true',
                            help="Recalculer uniquement les zones couvertes (tuiles existantes conservées)")

    def handle(self, lien, nom, zoom_max, reutiliser, emprise_seule, **opts):
        hote, projet, tache, titre = self._resoudre_tache(lien)
        nom = nom or titre or f'Orthophoto {tache[:8]}'
        self.stdout.write(f"Tâche WebODM : projet {projet}, tâche {tache}")

        # 2. Téléchargement du GeoTIFF
        dossier = os.path.join(settings.MEDIA_ROOT, 'orthophotos_commune')
        os.makedirs(dossier, exist_ok=True)
        tif = os.path.join(dossier, f'{tache}.tif')
        if not (reutiliser and os.path.exists(tif)):
            self._telecharger(f'{hote}/api/projects/{projet}/tasks/{tache}/download/orthophoto.tif', tif)

        # 3. Emprise réelle + résolution
        emprise, resolution = self._emprise_reelle(tif)
        self.stdout.write(f"Zones couvertes : {len(emprise)} · résolution {resolution} cm/px")

        # 4. Tuiles locales
        ortho = OrthophotoCommune.objects.filter(source=lien).first() or OrthophotoCommune(source=lien)
        if emprise_seule and ortho.pk:
            ortho.emprise, ortho.resolution = emprise, resolution
            ortho.save()
            for z in ortho.zones():
                self.stdout.write(f"  Zone {z['numero']} : {z['superficie_ha']} ha")
            return
        ortho.nom, ortho.emprise, ortho.resolution, ortho.zoom_max = nom, emprise, resolution, zoom_max
        ortho.fichier = os.path.relpath(tif, settings.MEDIA_ROOT).replace('\\', '/')
        ortho.tiles_url = 'en cours'
        ortho.save()
        sortie_rel = f'tiles/commune_ortho_{ortho.pk}'
        self._generer_tuiles(tif, os.path.join(settings.MEDIA_ROOT, sortie_rel), ortho.zoom_min, zoom_max)
        ortho.tiles_url = settings.MEDIA_URL + sortie_rel + '/{z}/{x}/{y}.png'
        ortho.save()

        for z in ortho.zones():
            self.stdout.write(f"  Zone {z['numero']} : {z['superficie_ha']} ha")
        self.stdout.write(self.style.SUCCESS(
            f"Orthophoto « {ortho.nom} » disponible sur la carte communale ({ortho.superficie / 10000:.1f} ha)."))

    # ------------------------------------------------------------------ étapes

    def _resoudre_tache(self, lien):
        u = urlparse(lien)
        hote = f'{u.scheme}://{u.netloc}'
        m = re.search(r'/api/projects/(\d+)/tasks/([0-9a-f-]{36})', lien)
        if m:
            return hote, m.group(1), m.group(2), ''
        if '/public/project/' not in lien:
            raise CommandError("Lien non reconnu : attendu un lien public WebODM (…/public/project/<id>/map/).")
        try:
            with urllib.request.urlopen(lien, timeout=30) as r:
                page = r.read().decode('utf-8')
        except OSError as e:
            raise CommandError(f"WebODM injoignable ({e}). Vérifiez qu'il est démarré.")
        items = re.search(r'data-map-items="([^"]+)"', page)
        if not items:
            raise CommandError("Aucune carte trouvée à ce lien (le projet est-il public ?).")
        taches = [i['meta']['task'] for i in json.loads(html.unescape(items.group(1)))
                  if 'orthophoto' in i['meta']['task'].get('tiles', [])]
        if not taches:
            raise CommandError("Ce projet ne contient pas d'orthophoto terminée.")
        if len(taches) > 1:
            self.stdout.write(self.style.WARNING(f"{len(taches)} tâches trouvées, import de la première."))
        titre = re.search(r'data-title="([^"]*)"', page)
        t = taches[0]
        return hote, str(t['project']), t['id'], html.unescape(titre.group(1)) if titre else ''

    def _telecharger(self, url, destination):
        self.stdout.write("Téléchargement du GeoTIFF…")
        tmp = destination + '.part'
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(tmp, 'wb') as f:
                total = int(r.headers.get('Content-Length') or 0)
                lu, palier = 0, 0
                while bloc := r.read(1024 * 1024):
                    f.write(bloc)
                    lu += len(bloc)
                    if total and lu * 10 // total > palier:
                        palier = lu * 10 // total
                        self.stdout.write(f"  {palier * 10} % ({lu // 2**20} / {total // 2**20} Mo)")
        except OSError as e:
            raise CommandError(f"Téléchargement impossible : {e}")
        os.replace(tmp, destination)

    def _emprise_reelle(self, tif):
        """Polygonise le masque des pixels réellement couverts (canal alpha)."""
        from osgeo import gdal, ogr, osr
        gdal.UseExceptions()
        ds = gdal.Open(tif)
        gt = ds.GetGeoTransform()
        resolution = round(abs(gt[1]) * 100, 2)  # m → cm (GeoTIFF WebODM en UTM)

        facteur = max(1, math.ceil(ds.RasterXSize / TAILLE_ANALYSE))
        w, h = math.ceil(ds.RasterXSize / facteur), math.ceil(ds.RasterYSize / facteur)
        bande = ds.GetRasterBand(ds.RasterCount)  # dernier canal = alpha pour WebODM
        if bande.GetColorInterpretation() != gdal.GCI_AlphaBand:
            bande = ds.GetRasterBand(1).GetMaskBand()
        masque = (bande.ReadAsArray(buf_xsize=w, buf_ysize=h) > 0).astype('uint8')

        mem = gdal.GetDriverByName('MEM').Create('', w, h, 1, gdal.GDT_Byte)
        mem.SetGeoTransform((gt[0], gt[1] * facteur, 0, gt[3], 0, gt[5] * facteur))
        mem.SetProjection(ds.GetProjection())
        mem.GetRasterBand(1).WriteArray(masque)

        srs = osr.SpatialReference(wkt=ds.GetProjection())
        # La source doit rester référencée tant que la couche est utilisée (sinon GDAL la libère)
        source = (ogr.GetDriverByName('MEM') or ogr.GetDriverByName('Memory')).CreateDataSource('zones')
        couche = source.CreateLayer('zones', srs=srs)
        couche.CreateField(ogr.FieldDefn('v', ogr.OFTInteger))
        gdal.Polygonize(mem.GetRasterBand(1), mem.GetRasterBand(1), couche, 0)

        epsg = int(srs.GetAuthorityCode(None) or UTM_SRID)
        parties = []
        for f in couche:
            g = GEOSGeometry(f.GetGeometryRef().ExportToWkt(), srid=epsg)
            # Contour extérieur seulement (on ignore les petits trous), lissé
            p = Polygon(g.exterior_ring, srid=epsg).simplify(SIMPLIFICATION_M, preserve_topology=True)
            if p.area >= ZONE_MIN_M2:
                parties.append(p)
        if not parties:
            raise CommandError("Aucune zone couverte détectée dans l'image.")
        # Fermeture morphologique : recolle les morceaux d'une même zone séparés
        # par une étroite bande sans image, sans fusionner deux zones distinctes.
        union = MultiPolygon(parties, srid=epsg).unary_union.buffer(FUSION_M).buffer(-FUSION_M)
        union = union.simplify(SIMPLIFICATION_M, preserve_topology=True)
        union = union if isinstance(union, MultiPolygon) else MultiPolygon(union, srid=epsg)
        union.transform(4326)
        return union, resolution

    def _generer_tuiles(self, tif, sortie, zmin, zmax):
        self.stdout.write(f"Génération des tuiles (zoom {zmin} à {zmax}), quelques minutes…")
        if os.path.isdir(sortie):
            shutil.rmtree(sortie)
        gdal2tiles = (
            shutil.which('gdal2tiles.py')
            or shutil.which('gdal2tiles')
            or os.path.join(os.path.dirname(sys.executable), 'gdal2tiles.py')
        )
        cmd = (
            [sys.executable, gdal2tiles]
            if gdal2tiles.endswith('.py')
            else [gdal2tiles]
        ) + [
            f'--zoom={zmin}-{zmax}', '--xyz', '--processes=4',
            '--webviewer=none', '--resampling=average', tif, sortie
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isdir(sortie):
            raise CommandError(f"gdal2tiles a échoué : {(r.stderr or '')[-800:]}")
