"""
Vues Django pour la gestion des réseaux linéaires et voiries (ReseauLineaire).
Architecture GeenkoDev : séparation stricte (Sélecteurs en lecture, Services en écriture).
Support de la modale d'ajout rapide, SlideOver dynamique et tracé cartographique Leaflet.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.decorators import domaine_required
from dossiers.models import ReseauLineaire
from ..forms import ReseauLineaireForm
from ..selectors import (
    get_reseaux_lineaires_queryset,
    get_reseau_lineaire_by_id,
    get_reseaux_lineaires_stats,
    get_reseaux_lineaires_geojson_for_carto,
)
from ..services import (
    creer_reseau_lineaire,
    modifier_reseau_lineaire,
    supprimer_reseau_lineaire,
)


@login_required
@domaine_required
def reseaux_lineaires_list(request):
    """Tableau de bord et inventaire des voies et réseaux de communication."""
    dossier = getattr(request, 'active_dossier', None)
    q = request.GET.get('q', '').strip()
    type_voie = request.GET.get('type_voie', '').strip()

    qs = get_reseaux_lineaires_queryset(
        dossier=dossier,
        q=q,
        type_voie=type_voie,
        sort='nom',
    )
    page = Paginator(qs, 20).get_page(request.GET.get('page'))

    form = ReseauLineaireForm(dossier=dossier)
    stats = get_reseaux_lineaires_stats(dossier)
    reseaux_geojson = get_reseaux_lineaires_geojson_for_carto(dossier)

    context = {
        'page_obj': page,
        'q': q,
        'type_voie': type_voie,
        'types_voie': ReseauLineaire.TYPES_VOIE,
        'stats': stats,
        'form': form,
        'reseaux_geojson': reseaux_geojson,
        'active_dossier': dossier,
    }
    return render(request, 'territoire/reseaux/list.html', context)


@login_required
@domaine_required
def reseau_lineaire_detail(request, pk):
    """Fiche détaillée d'un tronçon linéaire avec vue cartographique."""
    dossier = getattr(request, 'active_dossier', None)
    reseau = get_reseau_lineaire_by_id(pk, dossier=dossier)
    geom_json = reseau.geometrie.geojson if reseau.geometrie else 'null'

    context = {
        'voirie': reseau,
        'reseau': reseau,
        'geom_json': geom_json,
        'active_dossier': dossier,
    }
    return render(request, 'territoire/reseaux/detail.html', context)


@login_required
@domaine_required
def reseau_lineaire_create(request):
    """Création d'un tronçon linéaire."""
    dossier = getattr(request, 'active_dossier', None)
    form = ReseauLineaireForm(request.POST or None, dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        reseau = form.save(commit=False)
        if dossier and not reseau.dossier_id:
            reseau.dossier = dossier
        zone = reseau.zone_secteur
        reseau.save()
        messages.success(request, f"Tronçon « {reseau.nom or reseau.code} » enregistré ({reseau.longueur_km} km).")
        return redirect('territoire:reseaux')

    return render(request, 'territoire/reseaux/form.html', {
        'form': form,
        'action': 'Créer un tronçon de réseau linéaire',
        'active_dossier': dossier,
    })


@login_required
@domaine_required
def reseau_lineaire_update(request, pk):
    """Modification d'un tronçon linéaire."""
    dossier = getattr(request, 'active_dossier', None)
    reseau = get_reseau_lineaire_by_id(pk, dossier=dossier)
    form = ReseauLineaireForm(request.POST or None, instance=reseau, dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Tronçon « {reseau.nom or reseau.code} » mis à jour.")
        return redirect('territoire:reseau_detail', pk=reseau.pk)

    return render(request, 'territoire/reseaux/form.html', {
        'form': form,
        'obj': reseau,
        'action': f"Modifier {reseau.nom or reseau.code}",
        'active_dossier': dossier,
    })


@login_required
@domaine_required
def reseau_lineaire_delete(request, pk):
    """Suppression d'un tronçon linéaire."""
    dossier = getattr(request, 'active_dossier', None)
    reseau = get_reseau_lineaire_by_id(pk, dossier=dossier)

    if request.method == 'POST':
        libelle = reseau.nom or reseau.code
        supprimer_reseau_lineaire(reseau)
        messages.success(request, f"Tronçon « {libelle} » supprimé.")
        return redirect('territoire:reseaux')

    return render(request, 'territoire/generique/confirm_delete.html', {
        'obj': reseau,
        'back_url': 'territoire:reseaux',
    })
