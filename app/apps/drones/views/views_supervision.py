import json as _json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from accounts.decorators import domaine_required
from ..models import FluxVideo, Mission, PhotoDrone
from ..services import (
    arreter_diffusion,
    arreter_enregistrement,
    demarrer_diffusion,
    demarrer_enregistrement,
)


@login_required
@domaine_required
def perspectives(request):
    """Centre de supervision : carte temps réel, KPI, alertes et activité
    récente du territoire/campus. Le flux vidéo live (RTSP/HLS/WebRTC via MediaMTX) reste disponible."""
    from dossiers.models import Dossier, ZoneSecteur, UniteBatie, ReseauLineaire

    dossier = getattr(request, 'active_dossier', None) or Dossier.objects.first()

    dossier_geom_json = dossier.emprise.geojson if (dossier and dossier.emprise) else 'null'

    total_terrains_qs = UniteBatie.objects.filter(type_bati=UniteBatie.TYPE_SPORTIF)
    total_verts_qs = ZoneSecteur.objects.filter(type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE)
    if dossier:
        total_terrains_qs = total_terrains_qs.filter(dossier=dossier)
        total_verts_qs = total_verts_qs.filter(dossier=dossier)

    return render(request, 'drones/supervision/perspectives.html', {
        'flux_count': FluxVideo.objects.count(),
        'photos_count': PhotoDrone.objects.filter(mission__isnull=True).count(),
        'dossier': dossier,
        'dossier_geom_json': dossier_geom_json,
        'campus': dossier,
        'campus_geom_json': dossier_geom_json,
        'total_batiments': UniteBatie.objects.filter(dossier=dossier).count() if dossier else UniteBatie.objects.count(),
        'total_reseaux': ReseauLineaire.objects.filter(dossier=dossier).count() if dossier else ReseauLineaire.objects.count(),
        'total_voiries': ReseauLineaire.objects.filter(dossier=dossier).count() if dossier else ReseauLineaire.objects.count(),
        'total_terrains_sportifs': total_terrains_qs.count(),
        'total_espaces_verts': total_verts_qs.count(),
        'flux_videos_recentes': FluxVideo.objects.all()[:20],
    })


@login_required
@domaine_required
def supervision_donnees(request):
    """Endpoint JSON interrogé périodiquement (polling AJAX) par le Centre de
    supervision pour rafraîchir KPI, alertes et activité récente sans recharger la page."""
    from django.db.models import Q
    from urbanisme.models import NouvelleConstruction
    from dossiers.models import ZoneSecteur, UniteBatie, ReseauLineaire

    dossier = getattr(request, 'active_dossier', None)

    alertes = []
    nc_qs = NouvelleConstruction.objects.all()
    if dossier:
        nc_qs = nc_qs.filter(Q(dossier=dossier) | Q(zone_secteur__dossier=dossier)).distinct()

    for c in nc_qs.filter(statut=NouvelleConstruction.STATUT_EN_COURS).order_by('-date_demande')[:5]:
        alertes.append({
            'niveau': 'info',
            'icone': 'bi-building-add',
            'texte': f"Nouvelle demande de construction : « {c.nom_projet} » ({c.superficie_souhaitee:,.0f} m²)",
            'heure': c.date_demande.isoformat(),
        })
    for c in nc_qs.filter(
        statut=NouvelleConstruction.STATUT_EN_COURS, disponible=False
    ).order_by('-date_demande')[:5]:
        alertes.append({
            'niveau': 'warning',
            'icone': 'bi-exclamation-triangle-fill',
            'texte': f"Conflit spatial détecté : « {c.nom_projet} » — superficie insuffisante dans la zone souhaitée",
            'heure': c.date_demande.isoformat(),
        })

    mission_qs = Mission.objects.all()
    if dossier:
        mission_qs = mission_qs.filter(dossier=dossier)
    for m in mission_qs.order_by('-date_creation')[:3]:
        alertes.append({
            'niveau': 'info',
            'icone': 'bi-airplane-fill',
            'texte': f"Mission « {m.nom} » — {m.get_statut_display()}",
            'heure': m.date_creation.isoformat(),
        })
    alertes.sort(key=lambda a: a['heure'], reverse=True)

    activites = []
    bat_qs = UniteBatie.objects.all()
    res_qs = ReseauLineaire.objects.all()
    zs_qs = ZoneSecteur.objects.all()
    if dossier:
        bat_qs = bat_qs.filter(dossier=dossier)
        res_qs = res_qs.filter(dossier=dossier)
        zs_qs = zs_qs.filter(dossier=dossier)

    for b in bat_qs.order_by('-date_creation')[:5]:
        activites.append({
            'icone': 'bi-building', 'couleur': '#1E3A8A',
            'texte': f"Bâtiment recensé : « {b.nom} »", 'heure': b.created_at.isoformat()
        })
    for v in res_qs.order_by('-date_creation')[:5]:
        activites.append({
            'icone': 'bi-signpost-split-fill', 'couleur': '#A16207',
            'texte': f"Voie/Réseau ajouté : « {v.nom} »", 'heure': v.created_at.isoformat()
        })
    for z in zs_qs.order_by('-date_creation')[:5]:
        activites.append({
            'icone': 'bi-grid-3x3-gap', 'couleur': '#16A34A',
            'texte': f"Zone/Secteur créé : « {z.nom} » ({z.get_type_zone_display()})",
            'heure': z.created_at.isoformat()
        })

    return JsonResponse({
        'status': 'ok',
        'alertes': alertes[:8],
        'activites': activites[:10],
    })


@login_required
@domaine_required
def flux_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}

    rtsp_url = data.get('rtsp_url', 'rtsp://localhost:8554/drone').strip()
    nom = (data.get('nom') or '').strip()

    result = demarrer_enregistrement(request.user.pk, rtsp_url, nom)
    status_code = result.pop('status_code', 200)
    return JsonResponse(result, status=status_code)


@login_required
@domaine_required
def flux_stop(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    result = arreter_enregistrement(request.user.pk, request.user)
    status_code = result.pop('status_code', 200)
    return JsonResponse(result, status=status_code)


@login_required
@domaine_required
def flux_diffuser_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    try:
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Corps JSON invalide'}, status=400)

    video_id = data.get('video_id')
    rtsp_url = (data.get('rtsp_url') or '').strip()
    boucle = data.get('boucle', True)

    if not video_id:
        return JsonResponse({'error': 'Vidéo non spécifiée'}, status=400)
    if not rtsp_url:
        return JsonResponse({'error': 'URL RTSP de publication manquante'}, status=400)

    result = demarrer_diffusion(request.user.pk, video_id, rtsp_url, boucle)
    status_code = result.pop('status_code', 200)
    return JsonResponse(result, status=status_code)


@login_required
@domaine_required
def flux_diffuser_stop(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode POST requise'}, status=405)

    result = arreter_diffusion(request.user.pk)
    status_code = result.pop('status_code', 200)
    return JsonResponse(result, status=status_code)
