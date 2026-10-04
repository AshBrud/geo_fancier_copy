"""
Vues Django pour la gestion des subdivisions territoriales (ZoneSecteur).
Architecture GeenkoDev : séparation stricte (Sélecteurs en lecture, Services en écriture).
Prise en charge de la modale d'ajout direct, SlideOver et filtrage par Dossier actif.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.decorators import domaine_required
from dossiers.models import ZoneSecteur
from ..forms import ZoneSecteurForm
from ..selectors import (
    get_zones_secteurs_queryset,
    get_zone_secteur_by_id,
    get_zone_stats,
    get_zones_geojson_for_carto,
)
from ..services import (
    creer_zone_secteur,
    modifier_zone_secteur,
    supprimer_zone_secteur,
)


@login_required
@domaine_required
def zones_secteurs_list(request):
    """
    Tableau de bord et liste des subdivisions territoriales (Zones / Secteurs / Villages).
    - Table épurée avec lignes cliquables connectées au SlideOver
    - Modale d'ajout direct sans rechargement de page
    """
    dossier = getattr(request, 'active_dossier', None)
    q = request.GET.get('q', '').strip()
    type_zone = request.GET.get('type_zone', '').strip()
    statut = request.GET.get('statut', '').strip()

    qs = get_zones_secteurs_queryset(
        dossier=dossier,
        q=q,
        type_zone=type_zone,
        statut=statut,
        sort='nom',
    )
    page = Paginator(qs, 15).get_page(request.GET.get('page'))

    # Formulaire de création rapide pour la modale
    form = ZoneSecteurForm(dossier=dossier)

    # Données GeoJSON pour la vue cartographique globale
    zones_geojson = get_zones_geojson_for_carto(dossier)

    context = {
        'page_obj': page,
        'q': q,
        'type_zone': type_zone,
        'statut': statut,
        'types_zone': ZoneSecteur.TYPES_ZONE,
        'statuts': ZoneSecteur.STATUTS,
        'form': form,
        'zones_geojson': zones_geojson,
        'active_dossier': dossier,
    }
    return render(request, 'territoire/espaces/list.html', context)


@login_required
@domaine_required
def zone_secteur_detail(request, pk):
    """Fiche détaillée d'une subdivision territoriale avec carte Leaflet et unités bâties associées."""
    dossier = getattr(request, 'active_dossier', None)
    zone = get_zone_secteur_by_id(pk, dossier=dossier)
    stats = get_zone_stats(zone)
    unites_baties = zone.unites_baties.all().order_by('nom')

    geom_json = zone.geometrie.geojson if zone.geometrie else 'null'

    context = {
        'zone': zone,
        'stats': stats,
        'unites_baties': unites_baties,
        'geom_json': geom_json,
        'active_dossier': dossier,
    }
    return render(request, 'territoire/espaces/detail.html', context)


@login_required
@domaine_required
def zone_secteur_create(request):
    """Création d'une subdivision territoriale (traitement POST ou page dédiée)."""
    dossier = getattr(request, 'active_dossier', None)
    form = ZoneSecteurForm(request.POST or None, dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        zone = form.save(commit=False)
        if dossier and not zone.dossier_id:
            zone.dossier = dossier
        zone.save()
        messages.success(request, f"Zone « {zone.nom} » enregistrée avec succès ({zone.code}).")
        return redirect('territoire:zones')

    return render(request, 'territoire/espaces/form.html', {
        'form': form,
        'action': 'Créer une subdivision',
        'active_dossier': dossier,
    })


@login_required
@domaine_required
def zone_secteur_update(request, pk):
    """Modification d'une subdivision territoriale."""
    dossier = getattr(request, 'active_dossier', None)
    zone = get_zone_secteur_by_id(pk, dossier=dossier)
    form = ZoneSecteurForm(request.POST or None, instance=zone, dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Subdivision « {zone.nom} » mise à jour avec succès.")
        return redirect('territoire:zone_detail', pk=zone.pk)

    return render(request, 'territoire/espaces/form.html', {
        'form': form,
        'obj': zone,
        'action': f"Modifier {zone.nom}",
        'active_dossier': dossier,
    })


@login_required
@domaine_required
def zone_secteur_delete(request, pk):
    """Suppression d'une subdivision territoriale."""
    dossier = getattr(request, 'active_dossier', None)
    zone = get_zone_secteur_by_id(pk, dossier=dossier)

    if request.method == 'POST':
        nom = zone.nom
        supprimer_zone_secteur(zone)
        messages.success(request, f"Subdivision « {nom} » supprimée.")
        return redirect('territoire:zones')

    return render(request, 'territoire/generique/confirm_delete.html', {
        'obj': zone,
        'back_url': 'territoire:zones',
    })
