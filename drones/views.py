from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from datetime import date as _today, datetime
from django.core.paginator import Paginator
from django.db.models import Q, Avg
import json as _json
import os
import sys
import subprocess
import shutil
import signal as _signal
from .models import Orthophoto, FluxVideo, PhotoDrone
from .forms import OrthophotoImportForm
from accounts.decorators import domaine_required

# Enregistrements actifs (par utilisateur — clé = user.pk)
_active_recordings = {}


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


# ── Enregistrement flux live (FFmpeg) ────────────────────────────────────────

@login_required
@domaine_required
def flux_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    if not shutil.which('ffmpeg'):
        return JsonResponse({'error': 'FFmpeg non installé sur le serveur.'}, status=500)

    try:
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Corps JSON invalide'}, status=400)

    rtsp_url = data.get('rtsp_url', '').strip()
    nom      = data.get('nom', '').strip()
    if not rtsp_url:
        return JsonResponse({'error': 'URL RTSP manquante'}, status=400)

    uid = request.user.pk
    if uid in _active_recordings:
        return JsonResponse({'error': 'Un enregistrement est déjà en cours'}, status=400)

    ts       = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nom      = nom or f'Flux drone {ts}'
    filename = f'flux-drone-{ts}.mp4'
    save_dir = os.path.join(settings.MEDIA_ROOT, 'flux_videos')
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)

    cmd = [
        'ffmpeg', '-y',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-c', 'copy',
        '-movflags', 'frag_keyframe+empty_moov',
        filepath,
    ]

    kwargs = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    except Exception as e:
        return JsonResponse({'error': f'Impossible de démarrer FFmpeg : {e}'}, status=500)

    _active_recordings[uid] = {
        'proc':       proc,
        'filepath':   filepath,
        'nom':        nom,
        'start_time': datetime.now(),
        'rtsp_url':   rtsp_url,
    }
    return JsonResponse({'status': 'started', 'nom': nom})


@login_required
@domaine_required
def flux_stop(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    uid = request.user.pk
    rec = _active_recordings.pop(uid, None)
    if not rec:
        return JsonResponse({'error': 'Aucun enregistrement en cours'}, status=400)

    proc = rec['proc']
    try:
        if sys.platform == 'win32':
            proc.send_signal(_signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(_signal.SIGINT)
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    duree   = int((datetime.now() - rec['start_time']).total_seconds())
    filepath = rec['filepath']

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        rel   = os.path.relpath(filepath, settings.MEDIA_ROOT).replace('\\', '/')
        video = FluxVideo.objects.create(
            nom=rec['nom'],
            fichier=rel,
            duree_secondes=duree,
            taille_octets=os.path.getsize(filepath),
            source_rtsp=rec['rtsp_url'],
            operateur=request.user.get_full_name() or request.user.username,
        )
        return JsonResponse({
            'status':   'stopped',
            'id':       video.pk,
            'nom':      video.nom,
            'duree':    video.duree_formatee,
            'taille_mb': video.taille_mb,
        })

    return JsonResponse({'status': 'stopped', 'warning': 'Fichier vide ou non créé'})


# ── Liste des flux vidéos enregistrés ────────────────────────────────────────

@login_required
@domaine_required
def flux_videos_list(request):
    qs = FluxVideo.objects.all()
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    total_taille = sum(v.taille_octets or 0 for v in FluxVideo.objects.all())
    return render(request, 'drones/flux_videos_list.html', {
        'page_obj':     page,
        'total':        FluxVideo.objects.count(),
        'total_taille': round(total_taille / 1048576, 1),
    })


@login_required
@domaine_required
def flux_video_delete(request, pk):
    video = get_object_or_404(FluxVideo, pk=pk)
    if request.method == 'POST':
        if video.fichier and os.path.exists(video.fichier.path):
            os.remove(video.fichier.path)
        video.delete()
        messages.success(request, f'Vidéo « {video.nom} » supprimée.')
        return redirect('drones:flux_videos')
    return render(request, 'drones/confirm_delete.html', {'obj': video})


# ── Capture photo depuis flux live ───────────────────────────────────────────

@login_required
@domaine_required
def capture_photo(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requis'}, status=405)

    import base64
    from django.core.files.base import ContentFile

    try:
        data       = _json.loads(request.body)
        image_data = data.get('image', '')
        nom        = data.get('nom', '').strip()
    except Exception:
        return JsonResponse({'error': 'Données invalides'}, status=400)

    if not image_data or ';base64,' not in image_data:
        return JsonResponse({'error': 'Image manquante'}, status=400)

    fmt, imgstr = image_data.split(';base64,')
    ext         = fmt.split('/')[-1]          # jpeg ou png
    ts          = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nom         = nom or f'Capture {ts}'
    filename    = f'drone-{ts}.{ext}'

    try:
        content = ContentFile(base64.b64decode(imgstr))
    except Exception:
        return JsonResponse({'error': 'Décodage base64 échoué'}, status=400)

    photo = PhotoDrone(
        nom=nom,
        operateur=request.user.get_full_name() or request.user.username,
    )
    photo.image.save(filename, content, save=True)

    return JsonResponse({
        'status': 'ok',
        'id':     photo.pk,
        'nom':    photo.nom,
        'url':    photo.image.url,
    })


@login_required
@domaine_required
def photos_drone_list(request):
    qs   = PhotoDrone.objects.all()
    page = Paginator(qs, 16).get_page(request.GET.get('page'))
    return render(request, 'drones/photos_drone_list.html', {
        'page_obj': page,
        'total':    PhotoDrone.objects.count(),
    })


@login_required
@domaine_required
def photo_drone_delete(request, pk):
    photo = get_object_or_404(PhotoDrone, pk=pk)
    if request.method == 'POST':
        if photo.image and os.path.exists(photo.image.path):
            os.remove(photo.image.path)
        photo.delete()
        messages.success(request, f'Photo « {photo.nom} » supprimée.')
        return redirect('drones:photos_drone')
    return render(request, 'drones/confirm_delete.html', {'obj': photo})
