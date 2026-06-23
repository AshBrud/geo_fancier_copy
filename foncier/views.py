from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
import json
from .models import Espace, Batiment, FonctionBatiment, SuiviTravaux, SUPERFICIE_CAMPUS_M2
from .forms import EspaceForm, BatimentForm, SuiviTravauxForm
from accounts.models import CustomUser
from accounts.decorators import foncier_required, domaine_required


# --- Cartographie ---

@login_required
def cartographie(request):
    from drones.models import Orthophoto
    orthos = list(
        Orthophoto.objects.filter(tiles_url__gt='')
        .values('id', 'nom', 'date_prise', 'tiles_url', 'operateur')
        .order_by('-date_prise')
    )
    for o in orthos:
        o['date_mission'] = o['date_prise'].strftime('%d/%m/%Y') if o['date_prise'] else ''
    return render(request, 'cartographie/map.html', {
        'orthophotos_json': json.dumps(orthos, ensure_ascii=False, default=str),
        'nb_orthophotos': len(orthos),
        'total_espaces': Espace.objects.count(),
        'nb_espaces_libres': Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count(),
        'total_batiments': Batiment.objects.filter(est_actif=True).count(),
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

    # Constructions engagées par espace (via FK direct — 1 seule requête)
    nc_engagee_par_espace = {}
    for row in NC.objects.filter(
        statut__in=NC.STATUTS_ENGAGES,
        espace_souhaitee__isnull=False,
    ).values('espace_souhaitee_id', 'superficie_souhaitee'):
        eid = row['espace_souhaitee_id']
        nc_engagee_par_espace[eid] = nc_engagee_par_espace.get(eid, 0.0) + (row['superficie_souhaitee'] or 0)

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
        sc = (e.superficie or 0) * (e.taux_occupation / 100)
        if sc > 0 and (nc_engagee_par_espace.get(e.pk, 0) / sc) >= 0.80:
            nb_espaces_satures += 1

    # Enrichir chaque espace de la page avec les données de capacité
    for esp in page.object_list:
        if esp.type_espace in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE):
            sc  = (esp.superficie or 0) * (esp.taux_occupation / 100)
            se  = nc_engagee_par_espace.get(esp.pk, 0.0)
            pct = round(se / sc * 100, 1) if sc else 0.0
            esp.cap_constructible = round(sc)
            esp.cap_engagee       = round(se)
            esp.cap_nette         = round(max(0.0, sc - se))
            esp.cap_pct           = pct
            esp.cap_niveau        = 'danger' if pct >= 80 else ('warning' if pct >= 50 else 'success')
        else:
            esp.cap_constructible = None
        esp.nb_constructions = nc_count_par_espace.get(esp.pk, 0)

    return render(request, 'foncier/espaces_list.html', {
        'page_obj':      page,
        'q':             q,
        'type_filter':   type_filter,
        'sort':          sort,
        'types':         Espace.TYPES,
        'stats':         stats,
        'total_espaces': total_espaces,
        'total_superficie_ha':         round(total_superficie / 10000, 2),
        'superficie_campus_ha':        round(SUPERFICIE_CAMPUS_M2 / 10000, 2),
        'sup_constructible_totale':    round(sup_constructible_totale),
        'sup_constructible_totale_ha': round(sup_constructible_totale / 10000, 2),
        'nb_espaces_satures':          nb_espaces_satures,
    })


@login_required
@foncier_required
def espace_detail(request, pk):
    from constructions.models import NouvelleConstruction as NC

    espace = get_object_or_404(Espace, pk=pk)
    sup_brute        = espace.superficie or 0
    actif            = espace.type_espace in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE)
    sup_constructible = sup_brute * (espace.taux_occupation / 100) if actif else 0

    def _pks(statuts):
        base = NC.objects.filter(statut__in=statuts)
        pks  = set(base.filter(espace_souhaitee=espace).values_list('pk', flat=True))
        if espace.geometrie:
            pks.update(base.filter(
                zone_souhaitee__isnull=False,
                zone_souhaitee__intersects=espace.geometrie,
            ).values_list('pk', flat=True))
        return pks

    pks_eng = _pks(NC.STATUTS_ENGAGES)
    pks_att = _pks([NC.STATUT_ATTENTE])
    pks_all = _pks([s for s, _ in NC.STATUTS])

    qs_eng = NC.objects.filter(pk__in=pks_eng).select_related('demandeur').order_by('-date_demande')
    qs_att = NC.objects.filter(pk__in=pks_att).select_related('demandeur').order_by('-date_demande')
    qs_all = NC.objects.filter(pk__in=pks_all).select_related('demandeur').order_by('-date_demande')

    sup_engagee = sum(c.superficie_souhaitee or 0 for c in qs_eng)
    sup_attente = sum(c.superficie_souhaitee or 0 for c in qs_att)
    sup_nette   = max(0.0, sup_constructible - sup_engagee)
    pct_utilise = round(sup_engagee / sup_constructible * 100, 1) if sup_constructible else 0.0

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
        'sup_nette':             round(sup_nette),
        'sup_attente':           round(sup_attente),
        'pct_utilise':           pct_utilise,
        'pct_nette':             round(max(0, 100 - pct_utilise), 1),
        'niveau':                niveau,
        'constructions_engagees': qs_eng,
        'constructions_attente':  qs_att,
        'toutes_constructions':   qs_all,
        'batiments':             batiments,
        'geom_json':             geom_json,
    }
    return render(request, 'foncier/espace_detail.html', context)


@login_required
@domaine_required
def espace_create(request):
    form = EspaceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        espace = form.save()
        messages.success(request, f'Espace « {espace.nom} » créé avec succès.')
        return redirect('foncier:espaces')
    return render(request, 'foncier/espace_form.html', {
        'form': form, 'action': 'Ajouter un espace', 'obj': None
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
        'form': form, 'action': 'Modifier l\'espace', 'obj': espace
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
        'form': form, 'action': 'Ajouter un bâtiment', 'obj': None
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
        'form': form, 'action': 'Modifier le bâtiment', 'obj': bat
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
