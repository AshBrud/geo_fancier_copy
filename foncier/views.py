from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
import json
from .models import (
    Espace, Batiment, FonctionBatiment, SuiviTravaux, superficie_campus_totale,
    Terrain, EspaceVert, Voirie, Campus,
)
from .forms import (
    EspaceForm, BatimentForm, SuiviTravauxForm,
    TerrainForm, EspaceVertForm, VoirieForm,
)
from accounts.models import CustomUser
from accounts.decorators import foncier_required, domaine_required


# --- Cartographie ---

@login_required
def cartographie(request):
    from drones.models import Orthophoto, Mission
    from .models import Terrain, EspaceVert, Voirie, PointInteret
    ortho_qs = (
        Orthophoto.objects.filter(
            tiles_url__gt='',
            valide=True,
        )
        .filter(Q(mission__isnull=True) | Q(mission__statut=Mission.STATUT_INTEGREE))
        .order_by('-date_prise')
    )
    orthos = [
        {
            'id': o.id,
            'nom': o.nom,
            'date_prise': o.date_prise,
            'tiles_url': o.tiles_url,
            'operateur': o.operateur,
            'bounds': o.emprise.extent if o.emprise else None,
            'date_mission': o.date_prise.strftime('%d/%m/%Y') if o.date_prise else '',
        }
        for o in ortho_qs
    ]
    campus = Campus.objects.first()
    return render(request, 'cartographie/map.html', {
        'orthophotos_json': json.dumps(orthos, ensure_ascii=False, default=str),
        'nb_orthophotos': len(orthos),
        'total_espaces': Espace.objects.count(),
        'nb_espaces_libres': Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count(),
        'nb_espaces_reserves': Espace.objects.filter(type_espace=Espace.TYPE_RESERVE).count(),
        'nb_espaces_occupes': Espace.objects.filter(type_espace=Espace.TYPE_OCCUPE).count(),
        'total_batiments': Batiment.objects.filter(est_actif=True).count(),
        'nb_terrains': Terrain.objects.exclude(type_terrain__icontains='sport').count(),
        'nb_terrains_sportifs': Terrain.objects.filter(type_terrain__icontains='sport').count(),
        'nb_espaces_verts': EspaceVert.objects.count(),
        'nb_voiries': Voirie.objects.count(),
        'nb_points_interet': PointInteret.objects.count(),
        'campus': campus,
        'campus_geom_json': campus.geometrie.geojson if campus and campus.geometrie else 'null',
    })


# --- Espaces ---

@login_required
@foncier_required
def espaces_list(request):
    from constructions.models import NouvelleConstruction as NC

    qs = Espace.objects.all()
    q            = request.GET.get('q', '')
    type_filter  = request.GET.get('type', '')
    sort         = request.GET.get('sort', 'nom')

    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    if type_filter:
        qs = qs.filter(type_espace=type_filter)

    _VALID_SORTS = {'nom', '-nom', 'code', '-code', 'superficie', '-superficie'}
    qs = qs.order_by(sort if sort in _VALID_SORTS else 'nom')

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    # Stats globales par type
    stats = {t[0]: Espace.objects.filter(type_espace=t[0]).aggregate(
        count=Count('id'), total=Sum('superficie'))
        for t in Espace.TYPES}
    total_espaces    = Espace.objects.count()
    total_superficie = Espace.objects.aggregate(s=Sum('superficie'))['s'] or 0

    # Capacité constructible (espaces libres + occupés uniquement)
    espaces_actifs = list(Espace.objects.filter(
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE]
    ))
    sup_constructible_totale = sum(
        (e.superficie or 0) * (e.taux_occupation / 100) for e in espaces_actifs
    )
    pks_allouees = set()
    pks_allouees_libres = set()
    for e in espaces_actifs:
        pks = NC.pks_pour_espace(e)
        pks_allouees.update(pks)
        if e.type_espace == Espace.TYPE_LIBRE:
            pks_allouees_libres.update(pks)
    sup_allouee_totale = sum(
        c.superficie_souhaitee or 0
        for c in NC.objects.filter(pk__in=pks_allouees)
    ) if pks_allouees else 0.0
    sup_allouee_libre = sum(
        c.superficie_souhaitee or 0
        for c in NC.objects.filter(pk__in=pks_allouees_libres)
    ) if pks_allouees_libres else 0.0
    sup_occupee_par_espace = {
        e.pk: e.superficie_batie + e.superficie_terrains + e.superficie_espaces_verts
        for e in espaces_actifs
    }
    sup_batie_totale = sum(sup_occupee_par_espace.values())
    sup_batie_libre = sum(
        sup_occupee_par_espace[e.pk] for e in espaces_actifs if e.type_espace == Espace.TYPE_LIBRE
    )
    if Espace.TYPE_LIBRE in stats:
        stats[Espace.TYPE_LIBRE]['total'] = max(
            0.0, (stats[Espace.TYPE_LIBRE]['total'] or 0) - sup_allouee_libre - sup_batie_libre
        )
    sup_constructible_nette = max(
        0.0, sup_constructible_totale - sup_allouee_totale - sup_batie_totale
    )

    # Constructions engagées par espace (via FK direct — 1 seule requête)
    # Nb constructions totales par espace (via FK direct)
    nc_count_par_espace = dict(
        NC.objects.filter(espace_souhaitee__isnull=False)
        .values('espace_souhaitee_id')
        .annotate(n=Count('id'))
        .values_list('espace_souhaitee_id', 'n')
    )

    # Nb espaces saturés (>= 80%) — tous espaces actifs
    nb_espaces_satures = 0
    for e in espaces_actifs:
        bilan = NC.bilan_espace(e)
        if bilan['constructible'] > 0 and (bilan['occupee'] / bilan['constructible']) >= 0.80:
            nb_espaces_satures += 1

    # Enrichir chaque espace de la page avec les données de capacité
    for esp in page.object_list:
        if esp.type_espace in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE):
            bilan = NC.bilan_espace(esp)
            pct = bilan['pct']
            esp.cap_constructible = round(bilan['constructible'])
            esp.cap_engagee       = round(bilan['allouee'])
            esp.cap_nette         = round(bilan['nette'])
            esp.cap_pct           = pct
            esp.cap_niveau        = 'danger' if pct >= 80 else ('warning' if pct >= 50 else 'success')
        else:
            esp.cap_constructible = None
        esp.nb_constructions = nc_count_par_espace.get(esp.pk, 0)

    return render(request, 'foncier/espaces_list.html', {
        'campus':        Campus.objects.first(),
        'page_obj':      page,
        'q':             q,
        'type_filter':   type_filter,
        'sort':          sort,
        'types':         Espace.TYPES_SOUS_ESPACE,
        'stats':         stats,
        'total_espaces': total_espaces,
        'total_superficie_ha':         round(total_superficie / 10000, 2),
        'superficie_campus_ha':        round(superficie_campus_totale() / 10000, 2),
        'sup_constructible_totale':    round(sup_constructible_totale),
        'sup_constructible_totale_ha': round(sup_constructible_totale / 10000, 2),
        'sup_constructible_nette':     round(sup_constructible_nette),
        'sup_constructible_nette_ha':  round(sup_constructible_nette / 10000, 2),
        'nb_espaces_satures':          nb_espaces_satures,
    })


@login_required
@foncier_required
def campus_detail(request):
    campus = Campus.objects.first()
    if not campus:
        messages.info(request, "Aucun Campus n'est encore défini.")
        return redirect('foncier:espaces')

    sous_espaces = campus.sous_espaces.all().order_by('nom')
    return render(request, 'foncier/campus_detail.html', {
        'campus':               campus,
        'sous_espaces':         sous_espaces,
        'superficie_ha':        campus.superficie_ha,
        'superficie_occupee':   round(campus.superficie_occupee),
        'superficie_reservee':  round(campus.superficie_reservee),
        'superficie_libre':     round(campus.superficie_libre),
        'superficie_libre_ha':  round(campus.superficie_libre / 10000, 2),
        'geom_json':            campus.geometrie.geojson if campus.geometrie else 'null',
    })


@login_required
@foncier_required
def espace_detail(request, pk):
    from constructions.models import NouvelleConstruction as NC

    espace = get_object_or_404(Espace, pk=pk)
    sup_brute        = espace.superficie or 0
    actif            = espace.type_espace in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE)
    sup_constructible = sup_brute * (espace.taux_occupation / 100) if actif else 0

    pks_eng = NC.pks_pour_espace(espace, NC.STATUTS_ENGAGES)
    pks_att = NC.pks_pour_espace(espace, [NC.STATUT_EN_COURS])
    pks_all = NC.pks_pour_espace(espace, [s for s, _ in NC.STATUTS])

    qs_eng = NC.objects.filter(pk__in=pks_eng).select_related('demandeur').order_by('-date_demande')
    qs_att = NC.objects.filter(pk__in=pks_att).select_related('demandeur').order_by('-date_demande')
    qs_all = NC.objects.filter(pk__in=pks_all).select_related('demandeur').order_by('-date_demande')

    sup_engagee = sum(c.superficie_souhaitee or 0 for c in qs_eng)
    sup_attente = sum(c.superficie_souhaitee or 0 for c in qs_att)
    sup_batie   = espace.superficie_batie if actif else 0.0
    sup_terrains = espace.superficie_terrains if actif else 0.0
    sup_espaces_verts = espace.superficie_espaces_verts if actif else 0.0
    sup_occupee = sup_engagee + sup_batie + sup_terrains + sup_espaces_verts
    sup_nette   = max(0.0, sup_constructible - sup_occupee)
    pct_utilise = round(sup_occupee / sup_constructible * 100, 1) if sup_constructible else 0.0

    if pct_utilise >= 80:   niveau = 'danger'
    elif pct_utilise >= 50: niveau = 'warning'
    else:                   niveau = 'success'

    batiments = list(
        Batiment.objects.filter(geometrie__intersects=espace.geometrie).select_related('fonction')
    ) if espace.geometrie else []

    geom_json = espace.geometrie.geojson if espace.geometrie else 'null'

    context = {
        'espace':                espace,
        'actif':                 actif,
        'sup_constructible':     round(sup_constructible),
        'sup_engagee':           round(sup_engagee),
        'sup_batie':             round(sup_batie),
        'sup_terrains':          round(sup_terrains),
        'sup_espaces_verts':     round(sup_espaces_verts),
        'sup_occupee':           round(sup_occupee),
        'sup_nette':             round(sup_nette),
        'sup_attente':           round(sup_attente),
        'pct_utilise':           pct_utilise,
        'pct_nette':             round(max(0, 100 - pct_utilise), 1),
        'niveau':                niveau,
        'constructions_engagees': qs_eng,
        'constructions_attente':  qs_att,
        'batiments':             batiments,
        'geom_json':             geom_json,
    }
    return render(request, 'foncier/espace_detail.html', context)


@login_required
@domaine_required
def espace_create(request):
    campus = Campus.objects.first()
    if not campus:
        messages.error(request, "Aucun Campus n'est défini. Impossible de créer un sous-espace.")
        return redirect('foncier:espaces')

    form = EspaceForm(request.POST or None, instance=Espace(campus=campus))
    if request.method == 'POST' and form.is_valid():
        espace = form.save()
        messages.success(request, f'Sous-espace « {espace.nom} » créé avec succès.')
        return redirect('foncier:espaces')
    return render(request, 'foncier/espace_form.html', {
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
        return redirect('foncier:espaces')
    return render(request, 'foncier/espace_form.html', {
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
        return redirect('foncier:espaces')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': espace, 'type': 'l\'espace', 'back_url': 'foncier:espaces'
    })


# --- Bâtiments ---

def _espaces_libres_json():
    espaces = []
    for espace in Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).order_by('nom'):
        if not espace.geometrie:
            continue
        espaces.append({
            'type': 'Feature',
            'geometry': json.loads(espace.geometrie.geojson),
            'properties': {
                'id': espace.pk,
                'code': espace.code,
                'nom': espace.nom,
                'superficie': espace.superficie,
            },
        })
    return json.dumps(espaces, ensure_ascii=False)


@login_required
def batiments_list(request):
    qs = Batiment.objects.select_related('fonction').all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    total_batiments = Batiment.objects.count()
    nb_actifs = Batiment.objects.filter(est_actif=True).count()
    superficie_totale = Batiment.objects.aggregate(s=Sum('superficie'))['s'] or 0
    return render(request, 'foncier/batiments_list.html', {
        'page_obj': page, 'q': q,
        'total_batiments': total_batiments,
        'nb_actifs': nb_actifs,
        'superficie_totale': superficie_totale,
        'superficie_ha': round(superficie_totale / 10000, 2) if superficie_totale else 0,
    })


@login_required
def batiment_detail(request, pk):
    batiment = get_object_or_404(Batiment, pk=pk)
    return render(request, 'foncier/batiment_detail.html', {'batiment': batiment})


@login_required
@domaine_required
def batiment_create(request):
    form = BatimentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        bat = form.save()
        messages.success(request, f'Bâtiment « {bat.nom} » créé avec succès.')
        return redirect('foncier:batiments')
    return render(request, 'foncier/batiment_form.html', {
        'form': form,
        'action': 'Ajouter un bâtiment',
        'obj': None,
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def batiment_update(request, pk):
    bat = get_object_or_404(Batiment, pk=pk)
    form = BatimentForm(request.POST or None, request.FILES or None, instance=bat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Bâtiment « {bat.nom} » modifié.')
        return redirect('foncier:batiments')
    return render(request, 'foncier/batiment_form.html', {
        'form': form,
        'action': 'Modifier le bâtiment',
        'obj': bat,
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def batiment_delete(request, pk):
    bat = get_object_or_404(Batiment, pk=pk)
    if request.method == 'POST':
        nom = bat.nom
        bat.delete()
        messages.success(request, f'Bâtiment « {nom} » supprimé.')
        return redirect('foncier:batiments')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': bat, 'type': 'le bâtiment', 'back_url': 'foncier:batiments'
    })


@login_required
@domaine_required
def batiment_import_sig(request):
    import os
    import tempfile
    from django.core.management.base import CommandError
    from .forms import BatimentImportForm
    from .management.commands._sig_import import sync_batiments

    form = BatimentImportForm(request.POST or None, request.FILES or None)
    resultat = None

    if request.method == 'POST' and form.is_valid():
        fichier = form.cleaned_data['fichier']
        suffix = os.path.splitext(fichier.name)[1] or '.geojson'
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            for chunk in fichier.chunks():
                tmp.write(chunk)
            tmp.close()
            resultat = sync_batiments(
                tmp.name,
                source_crs=form.cleaned_data.get('source_crs') or None,
                dry_run=form.cleaned_data['dry_run'],
            )
            if resultat['created'] or resultat['updated']:
                verbe = 'Prévisualisation' if form.cleaned_data['dry_run'] else 'Import'
                messages.success(
                    request,
                    f"{verbe} terminé(e) : {resultat['created']} créé(s), "
                    f"{resultat['updated']} mis à jour, {resultat['skipped']} ignoré(s)."
                )
            else:
                messages.warning(request, "Aucun bâtiment valide trouvé dans ce fichier.")
        except CommandError as exc:
            messages.error(request, str(exc))
        finally:
            os.unlink(tmp.name)

    return render(request, 'foncier/batiment_import_sig.html', {
        'form': form,
        'resultat': resultat,
    })


# --- Suivi des travaux ---

@login_required
@foncier_required
def suivi_travaux_list(request):
    qs = SuiviTravaux.objects.select_related(
        'construction', 'construction__demandeur', 'maitre_ouvrage'
    ).all()
    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '')
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        qs = qs.filter(construction__nom_projet__icontains=q)

    nb_non_demarre = SuiviTravaux.objects.filter(statut=SuiviTravaux.STATUT_NON_DEMARRE).count()
    nb_en_cours    = SuiviTravaux.objects.filter(statut=SuiviTravaux.STATUT_EN_COURS).count()
    nb_termine     = SuiviTravaux.objects.filter(statut=SuiviTravaux.STATUT_TERMINE).count()

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'foncier/suivi_travaux_list.html', {
        'page_obj': page,
        'statut': statut,
        'q': q,
        'statuts': SuiviTravaux.STATUTS,
        'nb_non_demarre': nb_non_demarre,
        'nb_en_cours': nb_en_cours,
        'nb_termine': nb_termine,
        'total': SuiviTravaux.objects.count(),
    })


@login_required
@foncier_required
def suivi_travaux_update(request, pk):
    suivi = get_object_or_404(SuiviTravaux, pk=pk)
    if request.method == 'POST':
        form = SuiviTravauxForm(request.POST, instance=suivi)
        if form.is_valid():
            form.save()
            messages.success(request, f'Suivi de « {suivi.construction.nom_projet} » mis à jour.')
            return redirect('foncier:suivi_travaux')
    else:
        form = SuiviTravauxForm(instance=suivi)
    return render(request, 'foncier/suivi_travaux_form.html', {
        'form': form,
        'suivi': suivi,
        'statuts': SuiviTravaux.STATUTS,
        'utilisateurs': CustomUser.objects.filter(is_active=True).order_by('last_name', 'first_name'),
    })


# --- Terrains, Espaces verts, Voiries (couches SIG complémentaires) ----------

@login_required
@foncier_required
def terrains_list(request):
    qs = Terrain.objects.all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(type_terrain__icontains=q))
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    rows = [{
        'pk': t.pk, 'nom': f"{t.code} - {t.nom}" if t.code else t.nom,
        'sous_titre': t.type_terrain or '—',
        'badge': t.etat or '—',
        'mesure': f"{t.superficie:.0f} m²" if t.superficie else '—',
    } for t in page.object_list]
    return render(request, 'foncier/generic_list.html', {
        'page_obj': page, 'q': q, 'rows': rows,
        'title': 'Terrains', 'icon': 'bi-map-fill', 'color': '#2563EB',
        'add_label': 'Ajouter un terrain',
        'add_url': 'foncier:terrain_create',
        'detail_url': 'foncier:terrain_detail',
        'update_url': 'foncier:terrain_update',
        'delete_url': 'foncier:terrain_delete',
        'total': Terrain.objects.count(),
        'mesure_label': 'Superficie',
    })


@login_required
@foncier_required
def terrain_detail(request, pk):
    terrain = get_object_or_404(Terrain, pk=pk)
    return render(request, 'foncier/generic_detail.html', {
        'obj': terrain, 'title': terrain.nom, 'icon': 'bi-map-fill', 'color': '#2563EB',
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
        'update_url': 'foncier:terrain_update', 'delete_url': 'foncier:terrain_delete',
        'back_url': 'foncier:terrains',
    })


@login_required
@domaine_required
def terrain_create(request):
    form = TerrainForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        t = form.save()
        messages.success(request, f'Terrain « {t.nom} » créé avec succès.')
        return redirect('foncier:terrains')
    return render(request, 'foncier/generic_form.html', {
        'form': form, 'action': 'Ajouter un terrain', 'obj': None,
        'color': '#2563EB', 'geom_type': 'polygon', 'back_url': 'foncier:terrains',
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def terrain_update(request, pk):
    t = get_object_or_404(Terrain, pk=pk)
    form = TerrainForm(request.POST or None, request.FILES or None, instance=t)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Terrain « {t.nom} » modifié.')
        return redirect('foncier:terrains')
    return render(request, 'foncier/generic_form.html', {
        'form': form, 'action': 'Modifier le terrain', 'obj': t,
        'color': '#2563EB', 'geom_type': 'polygon', 'back_url': 'foncier:terrains',
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def terrain_delete(request, pk):
    t = get_object_or_404(Terrain, pk=pk)
    if request.method == 'POST':
        nom = t.nom
        t.delete()
        messages.success(request, f'Terrain « {nom} » supprimé.')
        return redirect('foncier:terrains')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': t, 'back_url': 'foncier:terrains'
    })


@login_required
@foncier_required
def espaces_verts_list(request):
    qs = EspaceVert.objects.all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(type_espace_vert__icontains=q))
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    rows = [{
        'pk': e.pk, 'nom': f"{e.code} - {e.nom}" if e.code else e.nom,
        'sous_titre': e.type_espace_vert or '—',
        'badge': e.etat or '—',
        'mesure': f"{e.superficie:.0f} m²" if e.superficie else '—',
    } for e in page.object_list]
    return render(request, 'foncier/generic_list.html', {
        'page_obj': page, 'q': q, 'rows': rows,
        'title': 'Espaces verts', 'icon': 'bi-tree-fill', 'color': '#22C55E',
        'add_label': 'Ajouter un espace vert',
        'add_url': 'foncier:espace_vert_create',
        'detail_url': 'foncier:espace_vert_detail',
        'update_url': 'foncier:espace_vert_update',
        'delete_url': 'foncier:espace_vert_delete',
        'total': EspaceVert.objects.count(),
        'mesure_label': 'Superficie',
    })


@login_required
@foncier_required
def espace_vert_detail(request, pk):
    ev = get_object_or_404(EspaceVert, pk=pk)
    return render(request, 'foncier/generic_detail.html', {
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
        'update_url': 'foncier:espace_vert_update', 'delete_url': 'foncier:espace_vert_delete',
        'back_url': 'foncier:espaces_verts',
    })


@login_required
@domaine_required
def espace_vert_create(request):
    form = EspaceVertForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        ev = form.save()
        messages.success(request, f'Espace vert « {ev.nom} » créé avec succès.')
        return redirect('foncier:espaces_verts')
    return render(request, 'foncier/generic_form.html', {
        'form': form, 'action': 'Ajouter un espace vert', 'obj': None,
        'color': '#22C55E', 'geom_type': 'polygon', 'back_url': 'foncier:espaces_verts',
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def espace_vert_update(request, pk):
    ev = get_object_or_404(EspaceVert, pk=pk)
    form = EspaceVertForm(request.POST or None, request.FILES or None, instance=ev)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Espace vert « {ev.nom} » modifié.')
        return redirect('foncier:espaces_verts')
    return render(request, 'foncier/generic_form.html', {
        'form': form, 'action': "Modifier l'espace vert", 'obj': ev,
        'color': '#22C55E', 'geom_type': 'polygon', 'back_url': 'foncier:espaces_verts',
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def espace_vert_delete(request, pk):
    ev = get_object_or_404(EspaceVert, pk=pk)
    if request.method == 'POST':
        nom = ev.nom
        ev.delete()
        messages.success(request, f'Espace vert « {nom} » supprimé.')
        return redirect('foncier:espaces_verts')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': ev, 'back_url': 'foncier:espaces_verts'
    })


@login_required
@foncier_required
def voiries_list(request):
    qs = Voirie.objects.all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(type_voirie__icontains=q))
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    rows = [{
        'pk': v.pk, 'nom': f"{v.code} - {v.nom}" if v.code else v.nom,
        'sous_titre': v.get_type_voirie_display() if v.type_voirie else '—',
        'badge': v.etat or '—',
        'mesure': f"{round(v.longueur)} m" if v.longueur else '—',
    } for v in page.object_list]
    return render(request, 'foncier/generic_list.html', {
        'page_obj': page, 'q': q, 'rows': rows,
        'title': 'Voiries', 'icon': 'bi-signpost-split-fill', 'color': '#A16207',
        'add_label': 'Ajouter une voirie',
        'add_url': 'foncier:voirie_create',
        'detail_url': 'foncier:voirie_detail',
        'update_url': 'foncier:voirie_update',
        'delete_url': 'foncier:voirie_delete',
        'total': Voirie.objects.count(),
        'mesure_label': 'Longueur',
    })


@login_required
@foncier_required
def voirie_detail(request, pk):
    v = get_object_or_404(Voirie, pk=pk)
    return render(request, 'foncier/generic_detail.html', {
        'obj': v, 'title': v.nom, 'icon': 'bi-signpost-split-fill', 'color': '#A16207',
        'champs': [
            ('Code', v.code or '—'),
            ('Type', v.get_type_voirie_display() if v.type_voirie else '—'),
            ('Revêtement', v.revetement or '—'),
            ('État', v.etat or '—'),
            ('Description', v.description or '—'),
            ('Longueur', f"{round(v.longueur)} m" if v.longueur else '—'),
            ('Actif', 'Oui' if v.est_actif else 'Non'),
            ('Observation', v.observation or '—'),
        ],
        'geojson': v.geometrie.geojson if v.geometrie else None,
        'update_url': 'foncier:voirie_update', 'delete_url': 'foncier:voirie_delete',
        'back_url': 'foncier:voiries',
    })


@login_required
@domaine_required
def voirie_create(request):
    form = VoirieForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        v = form.save()
        messages.success(request, f'Voirie « {v.nom} » créée avec succès.')
        return redirect('foncier:voiries')
    return render(request, 'foncier/generic_form.html', {
        'form': form, 'action': 'Ajouter une voirie', 'obj': None,
        'color': '#A16207', 'geom_type': 'line', 'back_url': 'foncier:voiries',
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def voirie_update(request, pk):
    v = get_object_or_404(Voirie, pk=pk)
    form = VoirieForm(request.POST or None, request.FILES or None, instance=v)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Voirie « {v.nom} » modifiée.')
        return redirect('foncier:voiries')
    return render(request, 'foncier/generic_form.html', {
        'form': form, 'action': 'Modifier la voirie', 'obj': v,
        'color': '#A16207', 'geom_type': 'line', 'back_url': 'foncier:voiries',
        'espaces_libres_json': _espaces_libres_json(),
    })


@login_required
@domaine_required
def voirie_delete(request, pk):
    v = get_object_or_404(Voirie, pk=pk)
    if request.method == 'POST':
        nom = v.nom
        v.delete()
        messages.success(request, f'Voirie « {nom} » supprimée.')
        return redirect('foncier:voiries')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': v, 'back_url': 'foncier:voiries'
    })
