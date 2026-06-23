from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date as _today
from django.core.paginator import Paginator
from django.db.models import Q, Avg
import json as _json
import os
from .models import Orthophoto
from .forms import OrthophotoImportForm
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

        minx = gt[0]
        maxy = gt[3]
        maxx = minx + width  * gt[1]
        miny = maxy + height * gt[5]

        res_x = abs(gt[1])

        src_srs = osr.SpatialReference()
        src_srs.ImportFromWkt(ds.GetProjection())
        tgt_srs = osr.SpatialReference()
        tgt_srs.ImportFromEPSG(4326)

        if src_srs.IsGeographic():
            emprise = Polygon.from_bbox((minx, miny, maxx, maxy))
            res_cm  = res_x * 111320 * 100
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
            res_cm  = res_x * 100

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


# ── Hub orthophotos ───────────────────────────────────────────────────────────

@login_required
@domaine_required
def orthophotos_list(request):
    """Hub de données drones — catalogue orthophotos + carte de couverture."""
    q = request.GET.get('q', '')

    qs = Orthophoto.objects.all().order_by('-date_prise')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(operateur__icontains=q))

    paginator = Paginator(qs, 12)
    page      = paginator.get_page(request.GET.get('page'))

    all_orthos  = Orthophoto.objects.all()
    res_moyenne = all_orthos.filter(resolution__isnull=False).aggregate(avg=Avg('resolution'))['avg']
    nb_georef   = all_orthos.filter(emprise__isnull=False).count()

    surface_ha = 0.0
    for ortho in all_orthos.filter(emprise__isnull=False):
        try:
            geom_utm = ortho.emprise.transform(32628, clone=True)
            surface_ha += geom_utm.area / 10000
        except Exception:
            pass

    features = []
    for ortho in all_orthos.filter(emprise__isnull=False):
        features.append({
            'type': 'Feature',
            'geometry': _json.loads(ortho.emprise.geojson),
            'properties': {
                'nom':        ortho.nom,
                'date':       str(ortho.date_prise),
                'resolution': ortho.resolution,
                'operateur':  ortho.operateur,
                'pk':         ortho.pk,
                'layer_type': 'orthophoto',
            },
        })

    return render(request, 'drones/orthophotos_list.html', {
        'page_obj':          page,
        'q':                 q,
        'total_orthophotos': all_orthos.count(),
        'nb_georeferencees': nb_georef,
        'res_moyenne':       round(res_moyenne, 1) if res_moyenne else None,
        'surface_ha':        round(surface_ha, 2),
        'coverage_geojson':  _json.dumps({'type': 'FeatureCollection', 'features': features}),
        'has_geodata':       bool(features),
    })


@login_required
@domaine_required
def import_orthophoto(request):
    """Import d'une orthophoto avec extraction automatique des métadonnées GeoTIFF."""
    form = OrthophotoImportForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        ortho = form.save(commit=False)
        ortho.date_prise = _today.today()
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
                    f'Orthophoto « {ortho.nom} » importée. Métadonnées géographiques non détectées.'
                )
        else:
            messages.success(request, f'Orthophoto « {ortho.nom} » importée.')

        return redirect('drones:missions')

    return render(request, 'drones/import_orthophoto.html', {'form': form})


@login_required
@domaine_required
def orthophoto_delete(request, pk):
    ortho = get_object_or_404(Orthophoto, pk=pk)
    if request.method == 'POST':
        ortho.delete()
        messages.success(request, 'Orthophoto supprimée.')
        return redirect('drones:missions')
    return render(request, 'drones/confirm_delete.html', {'obj': ortho})
