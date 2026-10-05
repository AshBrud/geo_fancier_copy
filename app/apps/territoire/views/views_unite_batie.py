"""
Vues Django pour la gestion du recensement bâti unifié (UniteBatie).
Architecture GeenkoDev : séparation stricte (Sélecteurs en lecture, Services en écriture).
Support modale d'ajout rapide, SlideOver dynamique, inspection et import SIG.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.decorators import domaine_required
from dossiers.models import UniteBatie, ZoneSecteur
from ..forms import UniteBatieForm
from ..selectors import (
    get_unites_baties_queryset,
    get_unite_batie_by_id,
    get_unites_baties_stats,
    get_unites_baties_geojson_for_carto,
    get_zones_secteurs_queryset,
)
from ..services import (
    creer_unite_batie,
    modifier_unite_batie,
    supprimer_unite_batie,
    importer_unites_baties_geojson,
)


@login_required
@domaine_required
def unites_baties_list(request):
    """
    Tableau de bord et inventaire des unités bâties (Bâtiments, Concessions, Infrastructures).
    """
    dossier = getattr(request, 'active_dossier', None)
    q = request.GET.get('q', '').strip()
    type_bati = request.GET.get('type_bati', '').strip()
    statut_occupation = request.GET.get('statut_occupation', '').strip()
    zone_id = request.GET.get('zone_id', '').strip()
    zone_id_int = int(zone_id) if zone_id and zone_id.isdigit() else None

    qs = get_unites_baties_queryset(
        dossier=dossier,
        q=q,
        type_bati=type_bati,
        statut_occupation=statut_occupation,
        zone_id=zone_id_int,
        sort='code',
    )
    page = Paginator(qs, 20).get_page(request.GET.get('page'))

    form = UniteBatieForm(dossier=dossier)
    stats = get_unites_baties_stats(dossier)
    zones = get_zones_secteurs_queryset(dossier=dossier)
    batiments_geojson = get_unites_baties_geojson_for_carto(dossier, zone_id=zone_id_int)

    context = {
        'page_obj': page,
        'q': q,
        'type_bati': type_bati,
        'statut_occupation': statut_occupation,
        'zone_id': zone_id_int,
        'types_bati': UniteBatie.TYPES_BATI,
        'statuts_occupation': UniteBatie.STATUTS_OCCUPATION,
        'zones': zones,
        'stats': stats,
        'form': form,
        'batiments_geojson': batiments_geojson,
        'active_dossier': dossier,
    }
    return render(request, 'territoire/batiments/list.html', context)


@login_required
@domaine_required
def unite_batie_detail(request, pk):
    """Fiche d'identité détaillée d'une unité bâtie."""
    dossier = getattr(request, 'active_dossier', None)
    unite = get_unite_batie_by_id(pk, dossier=dossier)
    geom_json = unite.geometrie.geojson if unite.geometrie else 'null'

    context = {
        'batiment': unite,
        'unite': unite,
        'geom_json': geom_json,
        'active_dossier': dossier,
    }
    return render(request, 'territoire/batiments/detail.html', context)


@login_required
@domaine_required
def unite_batie_create(request):
    """Création d'une unité bâtie."""
    dossier = getattr(request, 'active_dossier', None)
    form = UniteBatieForm(request.POST or None, request.FILES or None, dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        unite = form.save(commit=False)
        if dossier and not unite.dossier_id:
            unite.dossier = dossier
        unite.save()
        messages.success(request, f"Unité bâtie « {unite.nom or unite.code} » enregistrée avec succès.")
        return redirect('territoire:batiments')

    if request.method == 'GET':
        return redirect(reverse('territoire:batiments') + '?action=create')

    return render(request, 'territoire/batiments/form.html', {
        'form': form,
        'action': 'Recenser un bâtiment / concession',
        'active_dossier': dossier,
    })


@login_required
@domaine_required
def unite_batie_update(request, pk):
    """Modification d'une unité bâtie."""
    dossier = getattr(request, 'active_dossier', None)
    unite = get_unite_batie_by_id(pk, dossier=dossier)
    form = UniteBatieForm(request.POST or None, request.FILES or None, instance=unite, dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Unité bâtie « {unite.nom or unite.code} » mise à jour avec succès.")
        return redirect('territoire:batiment_detail', pk=unite.pk)

    return redirect('territoire:batiment_detail', pk=unite.pk)


@login_required
@domaine_required
def unite_batie_delete(request, pk):
    """Suppression d'une unité bâtie."""
    dossier = getattr(request, 'active_dossier', None)
    unite = get_unite_batie_by_id(pk, dossier=dossier)

    if request.method == 'POST':
        identifiant = unite.nom or unite.code
        supprimer_unite_batie(unite)
        messages.success(request, f"Unité bâtie « {identifiant} » supprimée.")
        return redirect('territoire:batiments')

    return render(request, 'territoire/generique/confirm_delete.html', {
        'obj': unite,
        'back_url': 'territoire:batiments',
    })


@login_required
@domaine_required
def unite_batie_import_sig(request):
    """Import SIG GeoJSON pour intégration en masse du bâti."""
    dossier = getattr(request, 'active_dossier', None)
    if request.method == 'POST' and request.FILES.get('geojson_file'):
        file = request.FILES['geojson_file']
        try:
            content = file.read().decode('utf-8')
            res = importer_unites_baties_geojson(dossier, content, user=request.user)
            messages.success(
                request,
                f"Import terminé avec succès : {res['created']} entités créées sur {res['total_features']}."
            )
            if res['errors']:
                messages.warning(request, f"{len(res['errors'])} entités ignorées ou en erreur.")
            return redirect('territoire:batiments')
        except Exception as e:
            messages.error(request, f"Échec de l'import SIG : {e}")

    return redirect('territoire:batiments')
