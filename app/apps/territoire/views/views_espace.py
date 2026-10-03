from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from accounts.decorators import foncier_required, domaine_required
from territoire.models import Espace, Campus, Batiment, superficie_campus_totale
from territoire.forms import EspaceForm
from territoire.selectors import (
    get_espaces_queryset,
    get_espace_by_id,
    get_espaces_stats_globales,
    enrich_espace_capacite,
)
from urbanisme.models import NouvelleConstruction as NC


@login_required
@foncier_required
def espaces_list(request):
    """
    Catalogue des sous-espaces fonciers du territoire :
    Affiche la grille/tableau des espaces avec jauge de saturation, capacité constructible,
    fiche SlideOver détaillée au clic, et modale d'ajout rapide (Zero-Page Create).
    """
    q = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    sort = request.GET.get('sort', 'nom')

    campus = Campus.objects.first()

    # Traitement soumission directe de la modale de création
    if request.method == 'POST' and 'submit_espace' in request.POST:
        if not (request.user.is_domaine_foncier or request.user.is_admin):
            messages.error(request, "Vous n'avez pas les droits nécessaires pour créer un espace.")
            return redirect('territoire:espaces')
        creation_form = EspaceForm(request.POST, instance=Espace(campus=campus))
        if creation_form.is_valid():
            espace = creation_form.save()
            messages.success(request, f"Sous-espace « {espace.nom} » créé avec succès.")
            return redirect('territoire:espaces')
        else:
            messages.error(request, "Erreur lors de la validation du sous-espace.")
    else:
        creation_form = EspaceForm(instance=Espace(campus=campus)) if campus else None

    qs = get_espaces_queryset(q=q, type_filter=type_filter, sort=sort)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    # Statistiques globales via selectors
    stats_data = get_espaces_stats_globales()

    # Constructions engagées par espace (FK direct)
    nc_count_par_espace = dict(
        NC.objects.filter(espace_souhaitee__isnull=False)
        .values('espace_souhaitee_id')
        .annotate(n=Count('id'))
        .values_list('espace_souhaitee_id', 'n')
    )

    # Enrichissement pour chaque espace affiché
    for esp in page.object_list:
        cap_info = enrich_espace_capacite(esp)
        esp.cap_constructible = cap_info['cap_constructible']
        esp.cap_engagee = cap_info['cap_engagee']
        esp.cap_nette = cap_info['cap_nette']
        esp.cap_pct = cap_info['cap_pct']
        esp.cap_niveau = cap_info['cap_niveau']
        esp.nb_constructions = nc_count_par_espace.get(esp.pk, 0)

    context = {
        'campus': campus,
        'page_obj': page,
        'q': q,
        'type_filter': type_filter,
        'sort': sort,
        'types': Espace.TYPES_SOUS_ESPACE,
        'stats': stats_data['stats'],
        'total_espaces': stats_data['total_espaces'],
        'total_superficie_ha': round(stats_data['total_superficie'] / 10000, 2),
        'superficie_campus_ha': round(superficie_campus_totale() / 10000, 2),
        'sup_constructible_totale': round(stats_data['sup_constructible_totale']),
        'sup_constructible_totale_ha': round(stats_data['sup_constructible_totale'] / 10000, 2),
        'sup_constructible_nette': round(stats_data['sup_constructible_nette']),
        'sup_constructible_nette_ha': round(stats_data['sup_constructible_nette'] / 10000, 2),
        'nb_espaces_satures': stats_data['nb_espaces_satures'],
        'creation_form': creation_form,
    }
    return render(request, 'territoire/espaces_list.html', context)


@login_required
@foncier_required
def campus_detail(request):
    campus = Campus.objects.first()
    if not campus:
        messages.info(request, "Aucun Campus n'est encore défini.")
        return redirect('territoire:espaces')

    sous_espaces = campus.sous_espaces.all().order_by('nom')
    return render(request, 'territoire/campus_detail.html', {
        'campus': campus,
        'sous_espaces': sous_espaces,
        'superficie_ha': campus.superficie_ha,
        'superficie_occupee': round(campus.superficie_occupee),
        'superficie_reservee': round(campus.superficie_reservee),
        'superficie_libre': round(campus.superficie_libre),
        'superficie_libre_ha': round(campus.superficie_libre / 10000, 2),
        'geom_json': campus.geometrie.geojson if campus.geometrie else 'null',
    })


@login_required
@foncier_required
def espace_detail(request, pk):
    espace = get_object_or_404(Espace, pk=pk)
    sup_brute = espace.superficie or 0
    actif = espace.type_espace in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE)
    sup_constructible = sup_brute * (espace.taux_occupation / 100) if actif else 0

    pks_eng = NC.pks_pour_espace(espace, NC.STATUTS_ENGAGES)
    pks_att = NC.pks_pour_espace(espace, [NC.STATUT_EN_COURS])

    qs_eng = NC.objects.filter(pk__in=pks_eng).select_related('demandeur').order_by('-date_demande')
    qs_att = NC.objects.filter(pk__in=pks_att).select_related('demandeur').order_by('-date_demande')

    sup_engagee = sum(c.superficie_souhaitee or 0 for c in qs_eng)
    sup_attente = sum(c.superficie_souhaitee or 0 for c in qs_att)
    sup_batie = espace.superficie_batie if actif else 0.0
    sup_terrains = espace.superficie_terrains if actif else 0.0
    sup_espaces_verts = espace.superficie_espaces_verts if actif else 0.0
    sup_occupee = sup_engagee + sup_batie + sup_terrains + sup_espaces_verts
    sup_nette = max(0.0, sup_constructible - sup_occupee)
    pct_utilise = round(sup_occupee / sup_constructible * 100, 1) if sup_constructible else 0.0

    niveau = 'danger' if pct_utilise >= 80 else ('warning' if pct_utilise >= 50 else 'success')

    batiments = list(
        Batiment.objects.filter(geometrie__intersects=espace.geometrie).select_related('fonction')
    ) if espace.geometrie else []

    context = {
        'espace': espace,
        'actif': actif,
        'sup_constructible': round(sup_constructible),
        'sup_engagee': round(sup_engagee),
        'sup_batie': round(sup_batie),
        'sup_terrains': round(sup_terrains),
        'sup_espaces_verts': round(sup_espaces_verts),
        'sup_occupee': round(sup_occupee),
        'sup_nette': round(sup_nette),
        'sup_attente': round(sup_attente),
        'pct_utilise': pct_utilise,
        'pct_nette': round(max(0, 100 - pct_utilise), 1),
        'niveau': niveau,
        'constructions_engagees': qs_eng,
        'constructions_attente': qs_att,
        'batiments': batiments,
        'geom_json': espace.geometrie.geojson if espace.geometrie else 'null',
    }
    return render(request, 'territoire/espace_detail.html', context)


@login_required
@domaine_required
def espace_create(request):
    campus = Campus.objects.first()
    if not campus:
        messages.error(request, "Aucun Campus n'est défini. Impossible de créer un sous-espace.")
        return redirect('territoire:espaces')

    form = EspaceForm(request.POST or None, instance=Espace(campus=campus))
    if request.method == 'POST' and form.is_valid():
        espace = form.save()
        messages.success(request, f'Sous-espace « {espace.nom} » créé avec succès.')
        return redirect('territoire:espaces')
    return render(request, 'territoire/espace_form.html', {
        'form': form, 'action': 'Ajouter un sous-espace', 'obj': None,
        'campus': campus, 'campus_geom_json': campus.geometrie.geojson,
    })


@login_required
@domaine_required
def espace_update(request, pk):
    espace = get_object_or_404(Espace, pk=pk)
    form = EspaceForm(request.POST or None, instance=espace)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Espace « {espace.nom} » modifié.')
        return redirect('territoire:espaces')
    return render(request, 'territoire/espace_form.html', {
        'form': form, 'action': 'Modifier l\'espace', 'obj': espace,
        'campus': espace.campus,
        'campus_geom_json': espace.campus.geometrie.geojson if espace.campus and espace.campus.geometrie else 'null',
    })


@login_required
@domaine_required
def espace_delete(request, pk):
    espace = get_object_or_404(Espace, pk=pk)
    if request.method == 'POST':
        nom = espace.nom
        espace.delete()
        messages.success(request, f'Espace « {nom} » supprimé.')
        return redirect('territoire:espaces')
    return render(request, 'territoire/confirm_delete.html', {
        'obj': espace, 'type': 'l\'espace', 'back_url': 'territoire:espaces'
    })
