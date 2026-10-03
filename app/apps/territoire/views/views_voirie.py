from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from accounts.decorators import foncier_required, domaine_required
from territoire.models import Voirie, EspaceVert
from territoire.forms import VoirieForm, EspaceVertForm
from territoire.selectors import (
    get_voiries_queryset,
    get_voirie_by_id,
    get_espaces_verts_queryset,
    get_espace_vert_by_id,
    get_espaces_libres_geojson,
)


@login_required
@foncier_required
def voiries_list(request):
    """
    Gestion des voiries, axes et réseaux routiers :
    Supporte la recherche, le SlideOver des caractéristiques linéaires,
    et la création directe via modale Bootstrap.
    """
    q = request.GET.get('q', '')

    if request.method == 'POST' and 'submit_voirie' in request.POST:
        if not (request.user.is_domaine_foncier or request.user.is_admin):
            messages.error(request, "Accès refusé. Privilèges requis pour ajouter une voirie.")
            return redirect('territoire:voiries')
        creation_form = VoirieForm(request.POST, request.FILES)
        if creation_form.is_valid():
            v = creation_form.save()
            messages.success(request, f"Voirie « {v.nom} » enregistrée avec succès.")
            return redirect('territoire:voiries')
        else:
            messages.error(request, "Veuillez corriger les champs du formulaire de voirie.")
    else:
        creation_form = VoirieForm()

    qs = get_voiries_queryset(q=q)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    rows = [{
        'pk': v.pk,
        'nom': f"{v.code} - {v.nom}" if v.code else v.nom,
        'code': v.code or '—',
        'raw_nom': v.nom,
        'sous_titre': v.get_type_voirie_display() if v.type_voirie else '—',
        'type_voirie': v.get_type_voirie_display() if v.type_voirie else '—',
        'badge': v.etat or '—',
        'etat': v.etat or '—',
        'mesure': f"{round(v.longueur)} m" if v.longueur else '—',
        'longueur': f"{round(v.longueur)} m" if v.longueur else '—',
        'longueur_km': f"{round(v.longueur / 1000, 2)} km" if v.longueur else '—',
        'revetement': v.revetement or '—',
        'description': v.description or 'Aucune description.',
        'observation': v.observation or 'Aucune observation.',
        'est_actif': 'Actif' if v.est_actif else 'Inactif',
        'est_actif_bool': v.est_actif,
        'photo_url': v.photo.url if v.photo else '',
        'update_url': f"/territoire/voiries/{v.pk}/modifier/",
        'delete_url': f"/territoire/voiries/{v.pk}/supprimer/",
    } for v in page.object_list]

    context = {
        'page_obj': page,
        'q': q,
        'rows': rows,
        'title': 'Voiries & Réseaux',
        'icon': 'bi-signpost-split-fill',
        'color': '#A16207',
        'add_label': 'Ajouter une voirie',
        'add_url': 'territoire:voirie_create',
        'detail_url': 'territoire:voirie_detail',
        'update_url': 'territoire:voirie_update',
        'delete_url': 'territoire:voirie_delete',
        'total': Voirie.objects.count(),
        'mesure_label': 'Longueur',
        'creation_form': creation_form,
        'geom_type': 'linestring',
    }
    return render(request, 'territoire/generic_list.html', context)


@login_required
@foncier_required
def voirie_detail(request, pk):
    v = get_object_or_404(Voirie, pk=pk)
    return render(request, 'territoire/generic_detail.html', {
        'obj': v, 'title': v.nom, 'icon': 'bi-signpost-split-fill', 'color': '#A16207',
        'champs': [
            ('Code', v.code or '—'),
            ('Type', v.get_type_voirie_display() if v.type_voirie else '—'),
            ('Revêtement', v.revetement or '—'),
            ('État', v.etat or '—'),
            ('Longueur', f"{round(v.longueur)} m" if v.longueur else '—'),
            ('Description', v.description or '—'),
            ('Actif', 'Oui' if v.est_actif else 'Non'),
            ('Observation', v.observation or '—'),
        ],
        'geojson': v.geometrie.geojson if v.geometrie else None,
        'update_url': 'territoire:voirie_update', 'delete_url': 'territoire:voirie_delete',
        'back_url': 'territoire:voiries',
    })


@login_required
@domaine_required
def voirie_create(request):
    form = VoirieForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        v = form.save()
        messages.success(request, f'Voirie « {v.nom} » créée avec succès.')
        return redirect('territoire:voiries')
    return render(request, 'territoire/generic_form.html', {
        'form': form, 'action': 'Ajouter une voirie', 'obj': None,
        'color': '#A16207', 'geom_type': 'linestring', 'back_url': 'territoire:voiries',
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def voirie_update(request, pk):
    v = get_object_or_404(Voirie, pk=pk)
    form = VoirieForm(request.POST or None, request.FILES or None, instance=v)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Voirie « {v.nom} » modifiée.')
        return redirect('territoire:voiries')
    return render(request, 'territoire/generic_form.html', {
        'form': form, 'action': 'Modifier la voirie', 'obj': v,
        'color': '#A16207', 'geom_type': 'linestring', 'back_url': 'territoire:voiries',
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def voirie_delete(request, pk):
    v = get_object_or_404(Voirie, pk=pk)
    if request.method == 'POST':
        nom = v.nom
        v.delete()
        messages.success(request, f'Voirie « {nom} » supprimée.')
        return redirect('territoire:voiries')
    return render(request, 'territoire/confirm_delete.html', {
        'obj': v, 'back_url': 'territoire:voiries'
    })


# --- Espaces Verts ---

@login_required
@foncier_required
def espaces_verts_list(request):
    q = request.GET.get('q', '')

    if request.method == 'POST' and 'submit_espace_vert' in request.POST:
        if not (request.user.is_domaine_foncier or request.user.is_admin):
            messages.error(request, "Accès refusé pour créer un espace vert.")
            return redirect('territoire:espaces_verts')
        creation_form = EspaceVertForm(request.POST, request.FILES)
        if creation_form.is_valid():
            ev = creation_form.save()
            messages.success(request, f"Espace vert « {ev.nom} » enregistré avec succès.")
            return redirect('territoire:espaces_verts')
        else:
            messages.error(request, "Erreur dans le formulaire de l'espace vert.")
    else:
        creation_form = EspaceVertForm()

    qs = get_espaces_verts_queryset(q=q)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    rows = [{
        'pk': e.pk,
        'nom': f"{e.code} - {e.nom}" if e.code else e.nom,
        'code': e.code or '—',
        'raw_nom': e.nom,
        'sous_titre': e.type_espace_vert or '—',
        'type_espace_vert': e.type_espace_vert or '—',
        'badge': e.etat or '—',
        'etat': e.etat or '—',
        'mesure': f"{e.superficie:.0f} m²" if e.superficie else '—',
        'superficie': f"{e.superficie:.0f} m²" if e.superficie else '—',
        'superficie_ha': f"{e.superficie_ha:.2f} ha" if e.superficie_ha else '—',
        'description': e.description or 'Aucune description.',
        'observation': e.observation or 'Aucune observation.',
        'est_actif': 'Actif' if e.est_actif else 'Inactif',
        'est_actif_bool': e.est_actif,
        'photo_url': e.photo.url if e.photo else '',
        'update_url': f"/territoire/espaces-verts/{e.pk}/modifier/",
        'delete_url': f"/territoire/espaces-verts/{e.pk}/supprimer/",
    } for e in page.object_list]

    context = {
        'page_obj': page,
        'q': q,
        'rows': rows,
        'title': 'Espaces verts',
        'icon': 'bi-tree-fill',
        'color': '#22C55E',
        'add_label': 'Ajouter un espace vert',
        'add_url': 'territoire:espace_vert_create',
        'detail_url': 'territoire:espace_vert_detail',
        'update_url': 'territoire:espace_vert_update',
        'delete_url': 'territoire:espace_vert_delete',
        'total': EspaceVert.objects.count(),
        'mesure_label': 'Superficie',
        'creation_form': creation_form,
    }
    return render(request, 'territoire/generic_list.html', context)


@login_required
@foncier_required
def espace_vert_detail(request, pk):
    ev = get_object_or_404(EspaceVert, pk=pk)
    return render(request, 'territoire/generic_detail.html', {
        'obj': ev, 'title': ev.nom, 'icon': 'bi-tree-fill', 'color': '#22C55E',
        'champs': [
            ('Code', ev.code or '—'),
            ('Type', ev.type_espace_vert or '—'),
            ('État', ev.etat or '—'),
            ('Description', ev.description or '—'),
            ('Superficie', f"{ev.superficie:.0f} m²" if ev.superficie else '—'),
            ('Actif', 'Oui' if ev.est_actif else 'Non'),
            ('Observation', ev.observation or '—'),
        ],
        'geojson': ev.geometrie.geojson if ev.geometrie else None,
        'update_url': 'territoire:espace_vert_update', 'delete_url': 'territoire:espace_vert_delete',
        'back_url': 'territoire:espaces_verts',
    })


@login_required
@domaine_required
def espace_vert_create(request):
    form = EspaceVertForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        ev = form.save()
        messages.success(request, f'Espace vert « {ev.nom} » créé avec succès.')
        return redirect('territoire:espaces_verts')
    return render(request, 'territoire/generic_form.html', {
        'form': form, 'action': 'Ajouter un espace vert', 'obj': None,
        'color': '#22C55E', 'geom_type': 'polygon', 'back_url': 'territoire:espaces_verts',
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def espace_vert_update(request, pk):
    ev = get_object_or_404(EspaceVert, pk=pk)
    form = EspaceVertForm(request.POST or None, request.FILES or None, instance=ev)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Espace vert « {ev.nom} » modifié.')
        return redirect('territoire:espaces_verts')
    return render(request, 'territoire/generic_form.html', {
        'form': form, 'action': "Modifier l'espace vert", 'obj': ev,
        'color': '#22C55E', 'geom_type': 'polygon', 'back_url': 'territoire:espaces_verts',
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def espace_vert_delete(request, pk):
    ev = get_object_or_404(EspaceVert, pk=pk)
    if request.method == 'POST':
        nom = ev.nom
        ev.delete()
        messages.success(request, f'Espace vert « {nom} » supprimé.')
        return redirect('territoire:espaces_verts')
    return render(request, 'territoire/confirm_delete.html', {
        'obj': ev, 'back_url': 'territoire:espaces_verts'
    })
