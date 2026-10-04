from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import domaine_required
from ..forms import MissionForm
from ..models import Mission, PhotoDrone
from ..selectors import (
    get_coverage_geojson,
    get_mission_by_id,
    get_mission_kpis,
    get_missions_queryset,
)


@login_required
@domaine_required
def mission_list(request):
    """Hub des missions de vol drone avec modale de création directe et SlideOver latéral."""
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '').strip()

    qs = get_missions_queryset(q=q, statut=statut)
    page_obj = Paginator(qs, 15).get_page(request.GET.get('page'))
    kpis = get_mission_kpis()
    coverage_geojson = get_coverage_geojson()
    has_geodata = coverage_geojson != '{"type": "FeatureCollection", "features": []}'

    creation_form = MissionForm()

    return render(request, 'drones/missions/list.html', {
        'page_obj': page_obj,
        'q': q,
        'statut': statut,
        'statuts': Mission.STATUTS,
        'nb_missions': kpis['nb_missions'],
        'total_orthophotos': kpis['total_orthophotos'],
        'surface_ha': kpis['surface_ha'],
        'nb_validees': kpis['nb_validees'],
        'creation_form': creation_form,
        'coverage_geojson': coverage_geojson,
        'has_geodata': has_geodata,
    })


@login_required
@domaine_required
def mission_create(request):
    """Création d'une nouvelle mission (par modale ou page dédiée)."""
    form = MissionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mission = form.save()
        messages.success(request, f'Mission « {mission.nom} » créée avec succès.')
        return redirect('drones:missions')
    return render(request, 'drones/missions/form.html', {'form': form, 'action': 'Nouvelle mission'})


@login_required
@domaine_required
def mission_update(request, pk):
    mission = get_mission_by_id(pk)
    form = MissionForm(request.POST or None, instance=mission)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Mission « {mission.nom} » mise à jour.')
        return redirect('drones:missions')
    return render(request, 'drones/missions/form.html', {
        'form': form,
        'mission': mission,
        'action': f'Modifier {mission.nom}',
    })


@login_required
@domaine_required
def mission_delete(request, pk):
    mission = get_mission_by_id(pk)
    if request.method == 'POST':
        nom = mission.nom
        mission.delete()
        messages.success(
            request,
            f'Mission « {nom} » supprimée. Les photos et orthophotos associées sont conservées.'
        )
        return redirect('drones:missions')
    return render(request, 'drones/communs/confirm_delete.html', {'obj': mission})


@login_required
@domaine_required
def mission_detail(request, pk):
    mission = get_mission_by_id(pk)
    orthophoto = mission.orthophotos.order_by('-date_ajout').first()
    photos = mission.photos.order_by('-date_capture')
    return render(request, 'drones/missions/detail.html', {
        'mission': mission,
        'orthophoto': orthophoto,
        'photos': photos,
    })


@login_required
@domaine_required
def mission_marquer_traitement(request, pk):
    mission = get_mission_by_id(pk)
    if request.method == 'POST' and mission.statut == Mission.STATUT_ATTENTE:
        mission.statut = Mission.STATUT_TRAITEMENT
        mission.save(update_fields=['statut', 'date_modification'])
        messages.success(request, f'Mission « {mission.nom} » marquée en traitement photogrammétrique.')
    return redirect('drones:mission_detail', pk=mission.pk)


@login_required
@domaine_required
def mission_photos_import(request, pk):
    mission = get_mission_by_id(pk)
    if request.method == 'POST':
        fichiers = request.FILES.getlist('images')
        if not fichiers:
            messages.error(request, 'Aucune photo sélectionnée.')
        else:
            for f in fichiers:
                PhotoDrone.objects.create(
                    nom=f.name,
                    image=f,
                    mission=mission,
                    operateur=mission.operateur,
                )
            if mission.statut == Mission.STATUT_ATTENTE:
                mission.statut = Mission.STATUT_TRAITEMENT
                mission.save(update_fields=['statut', 'date_modification'])
            messages.success(
                request,
                f'{len(fichiers)} photo(s) importée(s) pour la mission « {mission.nom} ».'
            )
            return redirect('drones:mission_detail', pk=mission.pk)
    return render(request, 'drones/missions/photos_import.html', {'mission': mission})
