from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from accounts.decorators import foncier_required, domaine_required
from territoire.models import Terrain
from territoire.forms import TerrainForm
from territoire.selectors import (
    get_terrains_queryset,
    get_terrain_by_id,
    get_espaces_libres_geojson,
)


@login_required
@foncier_required
def terrains_list(request):
    """
    Gestion des parcelles et terrains fonciers du territoire :
    Supporte la recherche, le SlideOver des caractéristiques parcellaires,
    et la création directe via modale Bootstrap (Zero-Page Create).
    """
    q = request.GET.get('q', '')

    # Soumission directe via Modale
    if request.method == 'POST' and 'submit_terrain' in request.POST:
        if not (request.user.is_domaine_foncier or request.user.is_admin):
            messages.error(request, "Accès refusé. Privilèges fonciers requis pour ajouter un terrain.")
            return redirect('territoire:terrains')
        creation_form = TerrainForm(request.POST, request.FILES)
        if creation_form.is_valid():
            t = creation_form.save()
            messages.success(request, f"Parcelle / Terrain « {t.nom} » enregistré avec succès.")
            return redirect('territoire:terrains')
        else:
            messages.error(request, "Veuillez corriger les champs du formulaire de terrain.")
    else:
        creation_form = TerrainForm()

    qs = get_terrains_queryset(q=q)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    rows = [{
        'pk': t.pk,
        'nom': f"{t.code} - {t.nom}" if t.code else t.nom,
        'code': t.code or '—',
        'raw_nom': t.nom,
        'sous_titre': t.type_terrain or '—',
        'type_terrain': t.type_terrain or '—',
        'badge': t.etat or '—',
        'etat': t.etat or '—',
        'mesure': f"{t.superficie:.0f} m²" if t.superficie else '—',
        'superficie': f"{t.superficie:.0f} m²" if t.superficie else '—',
        'superficie_ha': f"{t.superficie_ha:.2f} ha" if t.superficie_ha else '—',
        'description': t.description or 'Aucune description disponible.',
        'observation': t.observation or 'Aucune observation.',
        'est_actif': 'Actif' if t.est_actif else 'Inactif',
        'est_actif_bool': t.est_actif,
        'photo_url': t.photo.url if t.photo else '',
        'update_url': f"/territoire/terrains/{t.pk}/modifier/",
        'delete_url': f"/territoire/terrains/{t.pk}/supprimer/",
    } for t in page.object_list]

    context = {
        'page_obj': page,
        'q': q,
        'rows': rows,
        'title': 'Terrains & Parcelles',
        'icon': 'bi-bounding-box',
        'color': '#2563EB',
        'add_label': 'Ajouter un terrain',
        'add_url': 'territoire:terrain_create',
        'detail_url': 'territoire:terrain_detail',
        'update_url': 'territoire:terrain_update',
        'delete_url': 'territoire:terrain_delete',
        'total': Terrain.objects.count(),
        'mesure_label': 'Superficie',
        'creation_form': creation_form,
        'espaces_libres_json': get_espaces_libres_geojson(),
    }
    return render(request, 'territoire/generic_list.html', context)


@login_required
@foncier_required
def terrain_detail(request, pk):
    terrain = get_object_or_404(Terrain, pk=pk)
    return render(request, 'territoire/generic_detail.html', {
        'obj': terrain, 'title': terrain.nom, 'icon': 'bi-bounding-box', 'color': '#2563EB',
        'champs': [
            ('Code', terrain.code or '—'),
            ('Type', terrain.type_terrain or '—'),
            ('État', terrain.etat or '—'),
            ('Description', terrain.description or '—'),
            ('Superficie', f"{terrain.superficie:.0f} m²" if terrain.superficie else '—'),
            ('Actif', 'Oui' if terrain.est_actif else 'Non'),
            ('Observation', terrain.observation or '—'),
        ],
        'geojson': terrain.geometrie.geojson if terrain.geometrie else None,
        'update_url': 'territoire:terrain_update', 'delete_url': 'territoire:terrain_delete',
        'back_url': 'territoire:terrains',
    })


@login_required
@domaine_required
def terrain_create(request):
    form = TerrainForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        t = form.save()
        messages.success(request, f'Terrain « {t.nom} » créé avec succès.')
        return redirect('territoire:terrains')
    return render(request, 'territoire/generic_form.html', {
        'form': form, 'action': 'Ajouter un terrain', 'obj': None,
        'color': '#2563EB', 'geom_type': 'polygon', 'back_url': 'territoire:terrains',
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def terrain_update(request, pk):
    t = get_object_or_404(Terrain, pk=pk)
    form = TerrainForm(request.POST or None, request.FILES or None, instance=t)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Terrain « {t.nom} » modifié.')
        return redirect('territoire:terrains')
    return render(request, 'territoire/generic_form.html', {
        'form': form, 'action': 'Modifier le terrain', 'obj': t,
        'color': '#2563EB', 'geom_type': 'polygon', 'back_url': 'territoire:terrains',
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def terrain_delete(request, pk):
    t = get_object_or_404(Terrain, pk=pk)
    if request.method == 'POST':
        nom = t.nom
        t.delete()
        messages.success(request, f'Terrain « {nom} » supprimé.')
        return redirect('territoire:terrains')
    return render(request, 'territoire/confirm_delete.html', {
        'obj': t, 'back_url': 'territoire:terrains'
    })
