from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import os
from .models import MissionDrone, Orthophoto
from .forms import MissionDroneForm, OrthophotoImportForm
from accounts.decorators import domaine_required


# ── Extraction automatique depuis GeoTIFF (GDAL) ──────────────────────────────

def _extraire_metadata_geotiff(filepath):
    """Extrait emprise, résolution, dimensions et CRS depuis un GeoTIFF."""
    try:
        from osgeo import gdal, osr
        from django.contrib.gis.geos import Polygon, LinearRing

        ds = gdal.Open(filepath)
        if ds is None:
            return {}

        gt     = ds.GetGeoTransform()
        width  = ds.RasterXSize
        height = ds.RasterYSize

        # Coins de l'image dans le CRS source
        minx = gt[0]
        maxy = gt[3]
        maxx = minx + width  * gt[1]
        miny = maxy + height * gt[5]

        # Résolution en cm/pixel (pixel X en unités CRS)
        res_x = abs(gt[1])

        # Reprojection en WGS84 (EPSG:4326) si nécessaire
        src_srs = osr.SpatialReference()
        src_srs.ImportFromWkt(ds.GetProjection())
        tgt_srs = osr.SpatialReference()
        tgt_srs.ImportFromEPSG(4326)

        if src_srs.IsGeographic():
            # Déjà en degrés
            emprise = Polygon.from_bbox((minx, miny, maxx, maxy))
            res_cm  = res_x * 111320 * 100  # degrés → m → cm (approx)
        else:
            transform = osr.CoordinateTransformation(src_srs, tgt_srs)
            corners = [
                transform.TransformPoint(minx, miny),
                transform.TransformPoint(maxx, miny),
                transform.TransformPoint(maxx, maxy),
                transform.TransformPoint(minx, maxy),
                transform.TransformPoint(minx, miny),
            ]
            ring    = LinearRing([(c[1], c[0]) for c in corners])
            emprise = Polygon(ring, srid=4326)
            res_cm  = res_x * 100  # mètres → cm

        proj_desc = ''
        if src_srs.GetAttrValue('PROJCS'):
            proj_desc = src_srs.GetAttrValue('PROJCS')
        elif src_srs.GetAttrValue('GEOGCS'):
            proj_desc = src_srs.GetAttrValue('GEOGCS')

        ds = None
        return {
            'emprise':      emprise,
            'resolution':   round(res_cm, 4),
            'largeur_px':   width,
            'hauteur_px':   height,
            'systeme_proj': proj_desc[:200],
        }
    except Exception:
        return {}


# ── Extraction de zone depuis KML/KMZ/GPX (GDAL/OGR) ─────────────────────────

def _extraire_zone_kml(filepath):
    """Retourne le premier polygone trouvé dans un fichier KML/KMZ/GPX."""
    try:
        from django.contrib.gis.gdal import DataSource
        from django.contrib.gis.geos import GEOSGeometry

        ds = DataSource(filepath)
        for layer in ds:
            for feature in layer:
                geom = feature.geom
                wkt  = geom.wkt
                geos = GEOSGeometry(wkt, srid=4326)
                if geos.geom_type == 'Polygon':
                    return geos
                if geos.geom_type == 'MultiPolygon':
                    return geos[0]
        return None
    except Exception:
        return None


# ── Vues missions ─────────────────────────────────────────────────────────────

@login_required
@domaine_required
def missions_list(request):
    """Hub de données drones — catalogue orthophotos + carte de couverture."""
    import json as _json
    from django.db.models import Avg

    q          = request.GET.get('q', '')
    mission_id = request.GET.get('mission', '')

    # ── Catalogue orthophotos (données primaires) ──
    qs_orthos = Orthophoto.objects.select_related('mission').order_by('-date_prise')
    if q:
        qs_orthos = qs_orthos.filter(
            Q(nom__icontains=q) | Q(mission__nom__icontains=q)
        )
    if mission_id:
        qs_orthos = qs_orthos.filter(mission_id=mission_id)

    paginator = Paginator(qs_orthos, 12)
    page      = paginator.get_page(request.GET.get('page'))

    # ── Statistiques intelligentes ──
    all_orthos    = Orthophoto.objects.all()
    res_moyenne   = all_orthos.filter(resolution__isnull=False).aggregate(avg=Avg('resolution'))['avg']
    nb_georef     = all_orthos.filter(emprise__isnull=False).count()

    # Surface totale couverte (depuis emprises géoréférencées, projection UTM 28N Sénégal)
    surface_ha = 0.0
    for ortho in all_orthos.filter(emprise__isnull=False):
        try:
            geom_utm = ortho.emprise.transform(32628, clone=True)
            surface_ha += geom_utm.area / 10000
        except Exception:
            pass
    for mission in MissionDrone.objects.filter(zone_couverte__isnull=False):
        try:
            geom_utm = mission.zone_couverte.transform(32628, clone=True)
            surface_ha += geom_utm.area / 10000
        except Exception:
            pass

    # ── GeoJSON carte de couverture ──
    features = []
    for ortho in all_orthos.filter(emprise__isnull=False).select_related('mission'):
        features.append({
            'type': 'Feature',
            'geometry': _json.loads(ortho.emprise.geojson),
            'properties': {
                'layer_type': 'orthophoto',
                'nom':        ortho.nom,
                'mission':    ortho.mission.nom,
                'date':       str(ortho.date_prise),
                'resolution': ortho.resolution,
                'pk':         ortho.pk,
            },
        })
    for mission in MissionDrone.objects.filter(zone_couverte__isnull=False):
        features.append({
            'type': 'Feature',
            'geometry': _json.loads(mission.zone_couverte.geojson),
            'properties': {
                'layer_type': 'zone_vol',
                'nom':        mission.nom,
                'date':       str(mission.date_mission),
                'statut':     mission.get_statut_display(),
                'pk':         mission.pk,
            },
        })

    return render(request, 'drones/missions_list.html', {
        'page_obj':        page,
        'q':               q,
        'mission_id_actif': mission_id,
        'missions':        MissionDrone.objects.order_by('-date_mission'),
        # Stats
        'total_orthophotos': all_orthos.count(),
        'total_missions':    MissionDrone.objects.count(),
        'nb_georeferencees': nb_georef,
        'res_moyenne':       round(res_moyenne, 1) if res_moyenne else None,
        'surface_ha':        round(surface_ha, 2),
        'nb_avec_tuiles':    MissionDrone.objects.filter(tiles_url__gt='').count(),
        # Carte
        'coverage_geojson': _json.dumps({'type': 'FeatureCollection', 'features': features}),
        'has_geodata':      bool(features),
    })


@login_required
@domaine_required
def mission_detail(request, pk):
    mission = get_object_or_404(MissionDrone, pk=pk)
    return render(request, 'drones/mission_detail.html', {'mission': mission})


@login_required
@domaine_required
def mission_create(request):
    form = MissionDroneForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        mission = form.save(commit=False)
        # Import automatique zone_couverte depuis KML/KMZ/GPX
        if mission.fichier_kml:
            mission.save()  # sauvegarder d'abord pour avoir le chemin
            zone = _extraire_zone_kml(mission.fichier_kml.path)
            if zone:
                mission.zone_couverte = zone
                mission.save(update_fields=['zone_couverte'])
                messages.info(request, 'Zone couverte extraite automatiquement depuis le fichier.')
        else:
            mission.save()
        messages.success(request, f'Mission « {mission.nom} » créée.')
        return redirect('drones:missions')
    return render(request, 'drones/mission_form.html', {'form': form, 'action': 'Nouvelle mission'})


@login_required
@domaine_required
def mission_update(request, pk):
    mission = get_object_or_404(MissionDrone, pk=pk)
    form    = MissionDroneForm(request.POST or None, request.FILES or None, instance=mission)
    if request.method == 'POST' and form.is_valid():
        mission = form.save(commit=False)
        if mission.fichier_kml:
            mission.save()
            zone = _extraire_zone_kml(mission.fichier_kml.path)
            if zone:
                mission.zone_couverte = zone
                mission.save(update_fields=['zone_couverte'])
                messages.info(request, 'Zone couverte mise à jour depuis le fichier.')
        else:
            mission.save()
        messages.success(request, f'Mission « {mission.nom} » modifiée.')
        return redirect('drones:missions')
    return render(request, 'drones/mission_form.html', {
        'form': form, 'action': 'Modifier la mission', 'obj': mission
    })


@login_required
@domaine_required
def mission_delete(request, pk):
    mission = get_object_or_404(MissionDrone, pk=pk)
    if request.method == 'POST':
        nom = mission.nom
        mission.delete()
        messages.success(request, f'Mission « {nom} » supprimée.')
        return redirect('drones:missions')
    return render(request, 'drones/confirm_delete.html', {'obj': mission})


# ── Import orthophoto ─────────────────────────────────────────────────────────

@login_required
@domaine_required
def import_orthophoto(request, mission_pk=None):
    """Import d'une orthophoto avec extraction automatique des métadonnées GeoTIFF."""
    mission_initiale = get_object_or_404(MissionDrone, pk=mission_pk) if mission_pk else None
    missions         = MissionDrone.objects.order_by('-date_mission')

    form = OrthophotoImportForm(
        request.POST or None,
        request.FILES or None,
        initial={'mission': mission_initiale},
    )

    if request.method == 'POST' and form.is_valid():
        ortho = form.save(commit=False)

        # Sauvegarder d'abord pour avoir le chemin physique du fichier
        ortho.save()

        ext = os.path.splitext(ortho.fichier.name)[1].lower()
        if ext in ('.tif', '.tiff', '.geotiff'):
            meta = _extraire_metadata_geotiff(ortho.fichier.path)
            if meta:
                if meta.get('emprise') and not ortho.emprise:
                    ortho.emprise = meta['emprise']
                if meta.get('resolution') and not ortho.resolution:
                    ortho.resolution = meta['resolution']
                ortho.largeur_px   = meta.get('largeur_px')
                ortho.hauteur_px   = meta.get('hauteur_px')
                ortho.systeme_proj = meta.get('systeme_proj', '')
                ortho.save()
                messages.success(
                    request,
                    f'Orthophoto « {ortho.nom} » importée avec extraction automatique des métadonnées '
                    f'({ortho.largeur_px}×{ortho.hauteur_px}px, {ortho.resolution} cm/px).'
                )
            else:
                messages.warning(
                    request,
                    f'Orthophoto « {ortho.nom} » importée. Métadonnées géographiques non détectées '
                    f'(fichier non géoréférencé).'
                )
        else:
            messages.success(request, f'Orthophoto « {ortho.nom} » importée.')

        # Passer la mission au statut "traitée" automatiquement si ce n'est pas déjà le cas
        mission = ortho.mission
        if mission.statut == MissionDrone.STATUT_REALISE:
            mission.statut = MissionDrone.STATUT_TRAITE
            mission.save(update_fields=['statut'])
            messages.info(request, f'Mission « {mission.nom} » passée automatiquement au statut Traitée.')

        return redirect('drones:mission_detail', pk=ortho.mission.pk)

    return render(request, 'drones/import_orthophoto.html', {
        'form':             form,
        'mission_initiale': mission_initiale,
        'missions':         missions,
    })


@login_required
@domaine_required
def orthophoto_delete(request, pk):
    ortho = get_object_or_404(Orthophoto, pk=pk)
    if request.method == 'POST':
        mission_pk = ortho.mission.pk
        ortho.delete()
        messages.success(request, 'Orthophoto supprimée.')
        return redirect('drones:mission_detail', pk=mission_pk)
    return render(request, 'drones/confirm_delete.html', {'obj': ortho})
