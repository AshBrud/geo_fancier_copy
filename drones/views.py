from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from datetime import date as _today, datetime
from django.core.paginator import Paginator
from django.db.models import Q
import json as _json
import os
import sys
import subprocess
import shutil
import signal as _signal
from .models import Orthophoto, FluxVideo, PhotoDrone, Mission
from .forms import OrthophotoImportForm, MissionForm, FluxVideoImportForm
from accounts.decorators import domaine_required

# Enregistrements actifs (par utilisateur — clé = user.pk)
_active_recordings = {}
# Diffusions simulées actives (vidéo publiée en boucle vers MediaMTX comme flux live)
_active_broadcasts = {}


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


def _generer_tuiles_locales(ortho):
    """
    Génère une pyramide de tuiles XYZ à partir du GeoTIFF de l'orthophoto et les
    stocke dans MEDIA_ROOT/tiles/. Rend l'affichage sur la carte indépendant de
    WebODM : les tuiles restent disponibles même si WebODM est arrêté.
    """
    dossier = f'ortho_{ortho.pk}'
    sortie = os.path.join(settings.MEDIA_ROOT, 'tiles', dossier)
    if os.path.isdir(sortie):
        shutil.rmtree(sortie)

    gdal2tiles = os.path.join(os.path.dirname(sys.executable), 'gdal2tiles.py')
    cmd = [
        sys.executable, gdal2tiles,
        '--zoom=16-21', '--xyz', '--processes=2', '--webviewer=none',
        ortho.fichier.path, sortie,
    ]
    resultat = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if resultat.returncode != 0 or not os.path.isdir(sortie):
        raise RuntimeError(resultat.stderr[-500:] if resultat.stderr else 'gdal2tiles a échoué.')

    ortho.tiles_url = settings.MEDIA_URL + f'tiles/{dossier}/{{z}}/{{x}}/{{y}}.png'
    ortho.tuiles_locales = True
    ortho.save(update_fields=['tiles_url', 'tuiles_locales'])


# ── Hub missions ──────────────────────────────────────────────────────────────

@login_required
@domaine_required
def mission_list(request):
    """Hub principal — missions de vol, KPI de production cartographique et couverture."""
    q = request.GET.get('q', '')
    statut = request.GET.get('statut', '')

    qs = Mission.objects.all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(operateur__icontains=q))
    if statut:
        qs = qs.filter(statut=statut)

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get('page'))

    all_orthos  = Orthophoto.objects.all()

    surface_ha = 0.0
    for ortho in all_orthos.filter(emprise__isnull=False):
        sup = ortho.superficie_ha
        if sup:
            surface_ha += sup

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
                'tiles_url':  ortho.tiles_url,
            },
        })

    return render(request, 'drones/mission_list.html', {
        'page_obj':          page,
        'q':                 q,
        'statut':            statut,
        'statuts':           Mission.STATUTS,
        'nb_missions':       Mission.objects.count(),
        'total_orthophotos': all_orthos.count(),
        'nb_validees':       all_orthos.filter(valide=True).count(),
        'surface_ha':        round(surface_ha, 2),
        'coverage_geojson':  _json.dumps({'type': 'FeatureCollection', 'features': features}),
        'has_geodata':       bool(features),
    })


@login_required
@domaine_required
def mission_create(request):
    form = MissionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mission = form.save()
        messages.success(request, f'Mission « {mission.nom} » créée.')
        return redirect('drones:mission_detail', pk=mission.pk)
    return render(request, 'drones/mission_form.html', {'form': form, 'mission': None})


@login_required
@domaine_required
def mission_update(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    form = MissionForm(request.POST or None, instance=mission)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Mission « {mission.nom} » mise à jour.')
        return redirect('drones:mission_detail', pk=mission.pk)
    return render(request, 'drones/mission_form.html', {'form': form, 'mission': mission})


@login_required
@domaine_required
def mission_delete(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.method == 'POST':
        nom = mission.nom
        mission.delete()
        messages.success(request, f'Mission « {nom} » supprimée. Les photos et orthophotos associées sont conservées.')
        return redirect('drones:missions')
    return render(request, 'drones/confirm_delete.html', {'obj': mission})


@login_required
@domaine_required
def mission_detail(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    orthophoto = mission.orthophotos.order_by('-date_ajout').first()
    photos = mission.photos.order_by('-date_capture')
    return render(request, 'drones/mission_detail.html', {
        'mission':    mission,
        'orthophoto': orthophoto,
        'photos':     photos,
    })


@login_required
@domaine_required
def mission_marquer_traitement(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.method == 'POST' and mission.statut == Mission.STATUT_ATTENTE:
        mission.statut = Mission.STATUT_TRAITEMENT
        mission.save()
        messages.success(request, f'Mission « {mission.nom} » marquée en traitement photogrammétrique.')
    return redirect('drones:mission_detail', pk=mission.pk)


# ── Import photos (mission) ───────────────────────────────────────────────────

@login_required
@domaine_required
def mission_photos_import(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.method == 'POST':
        fichiers = request.FILES.getlist('images')
        if not fichiers:
            messages.error(request, 'Aucune photo sélectionnée.')
        else:
            for f in fichiers:
                PhotoDrone.objects.create(
                    nom=f.name, image=f, mission=mission,
                    operateur=mission.operateur,
                )
            if mission.statut == Mission.STATUT_ATTENTE:
                mission.statut = Mission.STATUT_TRAITEMENT
                mission.save()
            messages.success(request, f'{len(fichiers)} photo(s) importée(s) pour la mission « {mission.nom} ».')
            return redirect('drones:mission_detail', pk=mission.pk)
    return render(request, 'drones/mission_photos_import.html', {'mission': mission})


# ── Import orthophoto (autonome ou lié à une mission) ─────────────────────────

@login_required
@domaine_required
def import_orthophoto(request, pk=None):
    """Import d'une orthophoto avec extraction automatique des métadonnées GeoTIFF."""
    mission = get_object_or_404(Mission, pk=pk) if pk else None
    form = OrthophotoImportForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        ortho = form.save(commit=False)
        ortho.date_prise = _today.today()
        ortho.mission = mission
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

                try:
                    _generer_tuiles_locales(ortho)
                    messages.success(
                        request,
                        f'Orthophoto « {ortho.nom} » importée avec extraction automatique des métadonnées '
                        f'({ortho.largeur_px}×{ortho.hauteur_px}px, {ortho.resolution} cm/px) '
                        'et tuiles générées localement (affichage indépendant de WebODM).'
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f'Orthophoto « {ortho.nom} » importée avec métadonnées, mais la génération des '
                        f'tuiles locales a échoué ({e}). Renseignez une URL WebODM en secours si besoin.'
                    )
            else:
                messages.warning(
                    request,
                    f'Orthophoto « {ortho.nom} » importée. Métadonnées géographiques non détectées.'
                )
        else:
            messages.success(request, f'Orthophoto « {ortho.nom} » importée.')

        if mission and mission.statut == Mission.STATUT_TRAITEMENT:
            mission.statut = Mission.STATUT_TRAITEE
            mission.save()

        if mission:
            return redirect('drones:mission_detail', pk=mission.pk)
        return redirect('drones:missions')

    return render(request, 'drones/import_orthophoto.html', {'form': form, 'mission': mission})


@login_required
@domaine_required
def orthophoto_delete(request, pk):
    ortho = get_object_or_404(Orthophoto, pk=pk)
    mission_pk = ortho.mission_id
    if request.method == 'POST':
        ortho.delete()
        messages.success(request, 'Orthophoto supprimée.')
        if mission_pk:
            return redirect('drones:mission_detail', pk=mission_pk)
        return redirect('drones:missions')
    return render(request, 'drones/confirm_delete.html', {'obj': ortho})


@login_required
@domaine_required
def orthophoto_validate(request, pk):
    ortho = get_object_or_404(Orthophoto, pk=pk)
    if request.method == 'POST':
        ortho.valide = True
        ortho.date_validation = timezone.now()
        ortho.validateur = request.user
        ortho.save()
        messages.success(request, f'Orthophoto « {ortho.nom} » validée.')
    if ortho.mission_id:
        return redirect('drones:mission_detail', pk=ortho.mission_id)
    return redirect('drones:missions')


@login_required
@domaine_required
def orthophoto_integrate(request, pk):
    ortho = get_object_or_404(Orthophoto, pk=pk)
    if request.method == 'POST':
        if not ortho.valide:
            messages.error(request, "L'orthophoto doit être validée avant d'être intégrée à la cartographie.")
        elif not ortho.tiles_url:
            messages.error(request, "Une URL de tuiles (WebODM) est requise pour afficher l'orthophoto sur la carte.")
        else:
            if ortho.mission:
                ortho.mission.statut = Mission.STATUT_INTEGREE
                ortho.mission.save()
            messages.success(request, f'Orthophoto « {ortho.nom} » intégrée à la cartographie principale.')
    if ortho.mission_id:
        return redirect('drones:mission_detail', pk=ortho.mission_id)
    return redirect('drones:missions')


# ── Centre de supervision (monitoring temps réel du campus + flux drone) ─────

@login_required
@domaine_required
def perspectives(request):
    """Centre de supervision : carte temps réel, KPI, alertes et activité
    récente du campus. Le flux vidéo live (RTSP/HLS/WebRTC via MediaMTX) reste
    disponible ici — page de démonstration des capacités du SIG."""
    import json
    from foncier.models import Campus, Batiment, Voirie, Terrain, EspaceVert

    campus = Campus.objects.first()

    return render(request, 'drones/perspectives.html', {
        'flux_count': FluxVideo.objects.count(),
        'photos_count': PhotoDrone.objects.filter(mission__isnull=True).count(),
        'campus': campus,
        'campus_geom_json': campus.geometrie.geojson if campus and campus.geometrie else 'null',
        'total_batiments': Batiment.objects.count(),
        'total_voiries': Voirie.objects.count(),
        'total_terrains_sportifs': Terrain.objects.filter(type_terrain__icontains='sport').count(),
        'total_espaces_verts': EspaceVert.objects.count(),
        'flux_videos_recentes': FluxVideo.objects.all()[:20],
    })


@login_required
@domaine_required
def supervision_donnees(request):
    """Endpoint JSON interrogé périodiquement (polling AJAX) par le Centre de
    supervision pour rafraîchir KPI, alertes et activité récente sans recharger
    la page. Conçu pour être remplacé/complété par un canal WebSocket et une
    vraie télémétrie drone (DJI) le jour où ces flux seront connectés."""
    from constructions.models import NouvelleConstruction
    from foncier.models import Batiment, Voirie, EspaceVert, Espace

    derniere_mission = Mission.objects.order_by('-date_creation').first()

    # ── Alertes réelles, dérivées des données actuelles ──────────────────
    alertes = []
    for c in NouvelleConstruction.objects.filter(statut=NouvelleConstruction.STATUT_EN_COURS).order_by('-date_demande')[:5]:
        alertes.append({
            'niveau': 'info',
            'icone': 'bi-building-add',
            'texte': f"Nouvelle demande de construction : « {c.nom_projet} » ({c.superficie_souhaitee:,.0f} m²)",
            'heure': c.date_demande.isoformat(),
        })
    for c in NouvelleConstruction.objects.filter(
        statut=NouvelleConstruction.STATUT_EN_COURS, disponible=False
    ).order_by('-date_demande')[:5]:
        alertes.append({
            'niveau': 'warning',
            'icone': 'bi-exclamation-triangle-fill',
            'texte': f"Conflit spatial détecté : « {c.nom_projet} » — superficie insuffisante dans la zone souhaitée",
            'heure': c.date_demande.isoformat(),
        })
    for m in Mission.objects.order_by('-date_creation')[:3]:
        alertes.append({
            'niveau': 'info',
            'icone': 'bi-airplane-fill',
            'texte': f"Mission « {m.nom} » — {m.get_statut_display()}",
            'heure': m.date_creation.isoformat(),
        })
    alertes.sort(key=lambda a: a['heure'], reverse=True)

    # ── Activité récente, toutes couches confondues ──────────────────────
    activites = []
    for b in Batiment.objects.order_by('-date_ajout')[:5]:
        activites.append({'icone': 'bi-building', 'couleur': '#1E3A8A',
                           'texte': f"Bâtiment ajouté : « {b.nom} »", 'heure': b.date_ajout.isoformat()})
    for v in Voirie.objects.order_by('-date_creation')[:5]:
        activites.append({'icone': 'bi-signpost-split-fill', 'couleur': '#A16207',
                           'texte': f"Voirie ajoutée : « {v.nom} »", 'heure': v.date_creation.isoformat()})
    for ev in EspaceVert.objects.order_by('-date_creation')[:5]:
        activites.append({'icone': 'bi-tree-fill', 'couleur': '#22C55E',
                           'texte': f"Espace vert ajouté : « {ev.nom} »", 'heure': ev.date_creation.isoformat()})
    for e in Espace.objects.order_by('-date_creation')[:5]:
        activites.append({'icone': 'bi-grid-3x3-gap', 'couleur': '#16A34A',
                           'texte': f"Sous-espace créé : « {e.nom} » ({e.get_type_espace_display()})",
                           'heure': e.date_creation.isoformat()})
    for c in NouvelleConstruction.objects.filter(
        statut=NouvelleConstruction.STATUT_APPROUVE
    ).order_by('-date_modification')[:5]:
        activites.append({'icone': 'bi-check-circle-fill', 'couleur': '#15803d',
                           'texte': f"Construction validée : « {c.nom_projet} »",
                           'heure': c.date_modification.isoformat()})
    for m in Mission.objects.order_by('-date_creation')[:5]:
        activites.append({'icone': 'bi-airplane-fill', 'couleur': '#4338ca',
                           'texte': f"Mission drone lancée : « {m.nom} »",
                           'heure': m.date_creation.isoformat()})
    activites.sort(key=lambda a: a['heure'], reverse=True)

    return JsonResponse({
        'kpi': {
            'nb_missions': Mission.objects.count(),
            'derniere_mission': derniere_mission.nom if derniere_mission else None,
            'derniere_mission_statut': derniere_mission.get_statut_display() if derniere_mission else None,
            'derniere_maj': timezone.now().isoformat(),
            'utilisateur': request.user.get_full_name() or request.user.username,
            'etat_serveur': 'operationnel',
        },
        'alertes': alertes[:8],
        'activites': activites[:10],
    })


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


# ── Diffusion simulée d'une vidéo enregistrée comme flux live (FFmpeg → MediaMTX) ──

@login_required
@domaine_required
def flux_diffuser_start(request):
    """Republie en boucle un fichier vidéo déjà stocké vers le serveur MediaMTX
    (protocole RTSP), afin qu'il apparaisse comme un flux live dans le panneau
    HLS/WebRTC — utile pour démontrer le SIG sans drone réellement connecté."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    if not shutil.which('ffmpeg'):
        return JsonResponse({'error': 'FFmpeg non installé sur le serveur.'}, status=500)

    try:
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Corps JSON invalide'}, status=400)

    video_id = data.get('video_id')
    rtsp_url = (data.get('rtsp_url') or '').strip()
    boucle   = data.get('boucle', True)

    if not video_id:
        return JsonResponse({'error': 'Vidéo non spécifiée'}, status=400)
    if not rtsp_url:
        return JsonResponse({'error': 'URL RTSP de publication manquante'}, status=400)

    video = get_object_or_404(FluxVideo, pk=video_id)
    if not (video.fichier and os.path.exists(video.fichier.path)):
        return JsonResponse({'error': 'Fichier vidéo introuvable sur le serveur.'}, status=404)

    uid = request.user.pk
    if uid in _active_broadcasts:
        return JsonResponse({'error': 'Une diffusion est déjà en cours'}, status=400)

    cmd = ['ffmpeg', '-re']
    if boucle:
        cmd += ['-stream_loop', '-1']
    cmd += [
        '-i', video.fichier.path,
        '-c', 'copy',
        '-f', 'rtsp',
        '-rtsp_transport', 'tcp',
        rtsp_url,
    ]

    kwargs = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    except Exception as e:
        return JsonResponse({'error': f'Impossible de démarrer FFmpeg : {e}'}, status=500)

    _active_broadcasts[uid] = {
        'proc':       proc,
        'video':      video.nom,
        'rtsp_url':   rtsp_url,
        'start_time': datetime.now(),
    }
    return JsonResponse({'status': 'started', 'nom': video.nom})


@login_required
@domaine_required
def flux_diffuser_stop(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    uid = request.user.pk
    rec = _active_broadcasts.pop(uid, None)
    if not rec:
        return JsonResponse({'error': 'Aucune diffusion en cours'}, status=400)

    proc = rec['proc']
    try:
        if sys.platform == 'win32':
            proc.send_signal(_signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(_signal.SIGINT)
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    return JsonResponse({'status': 'stopped'})


def _duree_video_secondes(filepath):
    """Interroge ffprobe (si présent) pour récupérer la durée d'un fichier vidéo."""
    if not shutil.which('ffprobe'):
        return None
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15,
        )
        return int(float(out.stdout.decode().strip()))
    except Exception:
        return None


# ── Import d'une vidéo déjà enregistrée (carte SD, export DJI…) ──────────────

@login_required
@domaine_required
def flux_video_import(request):
    """Import manuel d'un fichier vidéo existant (ex. export carte SD du drone)
    dans le Centre de supervision, en complément de l'enregistrement live FFmpeg."""
    form = FluxVideoImportForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        video = form.save(commit=False)
        video.taille_octets = video.fichier.size
        if not video.operateur:
            video.operateur = request.user.get_full_name() or request.user.username
        video.save()
        video.duree_secondes = _duree_video_secondes(video.fichier.path)
        video.save(update_fields=['duree_secondes'])
        messages.success(request, f'Vidéo « {video.nom} » importée avec succès.')
        return redirect('drones:flux_videos')

    return render(request, 'drones/flux_video_import.html', {'form': form})


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
        mission_id = data.get('mission_id')
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

    mission = Mission.objects.filter(pk=mission_id).first() if mission_id else None

    photo = PhotoDrone(
        nom=nom,
        mission=mission,
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
