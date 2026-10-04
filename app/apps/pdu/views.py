from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from dossiers.models import ZoneSecteur, UniteBatie
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction
from accounts.decorators import foncier_required
import json


@login_required
@foncier_required
def statistiques(request):
    from django.db.models.functions import ExtractYear
    from urbanisme.models import HistoriqueConstruction as HC, NouvelleConstruction as NC

    dossier = getattr(request, 'active_dossier', None)

    total_sup_m2 = 0.0
    zs_qs = ZoneSecteur.objects.filter(dossier=dossier) if dossier else ZoneSecteur.objects.all()

    if dossier and dossier.superficie_m2:
        total_sup_m2 = float(dossier.superficie_m2)
    elif dossier and dossier.emprise:
        try:
            srid = getattr(dossier, 'srid_projection', 32628) or 32628
            geom_utm = dossier.emprise.transform(srid, clone=True)
            total_sup_m2 = float(geom_utm.area)
        except Exception:
            total_sup_m2 = float(zs_qs.aggregate(s=Sum('superficie_m2'))['s'] or 0.0)
    else:
        total_sup_m2 = float(zs_qs.aggregate(s=Sum('superficie_m2'))['s'] or 0.0)

    total_sup_ha = round(total_sup_m2 / 10000, 2)

    # ── Zones territoriales par type ──────────────────────────────────────
    zs_base = ZoneSecteur.objects.filter(dossier=dossier) if dossier else ZoneSecteur.objects.all()
    espaces_raw = zs_base.values('type_zone').annotate(
        count=Count('id'), superficie=Sum('superficie_m2')
    )

    COULEURS_TYPES = {
        ZoneSecteur.TYPE_VILLAGE: '#10b981',
        ZoneSecteur.TYPE_QUARTIER: '#6366f1',
        ZoneSecteur.TYPE_SECTEUR_CAMPUS: '#0284c7',
        ZoneSecteur.TYPE_ESPACE_LIBRE: '#22c55e',
        ZoneSecteur.TYPE_ESPACE_RESERVE: '#f59e0b',
        ZoneSecteur.TYPE_ZONE_AGRICOLE: '#84cc16',
        ZoneSecteur.TYPE_ZONE_ACTIVITE: '#ec4899',
        ZoneSecteur.TYPE_AUTRE: '#94a3b8',
    }
    types_dict = dict(ZoneSecteur.TYPES_ZONE)

    stats_enrichis = []
    for item in espaces_raw:
        sup_ha = round((item['superficie'] or 0) / 10000, 2)
        pct = round((item['superficie'] or 0) / total_sup_m2 * 100, 1) if total_sup_m2 else 0
        tz = item['type_zone']
        stats_enrichis.append({
            'type_espace':   tz,
            'label':         types_dict.get(tz, tz),
            'couleur':       COULEURS_TYPES.get(tz, '#94a3b8'),
            'count':         item['count'],
            'superficie_ha': sup_ha,
            'pourcentage':   pct,
        })
    stats_enrichis.sort(key=lambda x: x['superficie_ha'], reverse=True)

    def _sup_type(t):
        return zs_base.filter(type_zone=t).aggregate(s=Sum('superficie_m2'))['s'] or 0

    sup_libre_m2    = _sup_type(ZoneSecteur.TYPE_ESPACE_LIBRE)
    sup_occupee_m2  = (
        _sup_type(ZoneSecteur.TYPE_VILLAGE) +
        _sup_type(ZoneSecteur.TYPE_QUARTIER) +
        _sup_type(ZoneSecteur.TYPE_SECTEUR_CAMPUS) +
        _sup_type(ZoneSecteur.TYPE_ZONE_ACTIVITE)
    )
    sup_reservee_m2 = _sup_type(ZoneSecteur.TYPE_ESPACE_RESERVE)

    taux_libre   = round(sup_libre_m2    / total_sup_m2 * 100, 1) if total_sup_m2 else 0
    taux_occupe  = round(sup_occupee_m2  / total_sup_m2 * 100, 1) if total_sup_m2 else 0
    taux_reserve = round(sup_reservee_m2 / total_sup_m2 * 100, 1) if total_sup_m2 else 0

    nb_libres    = zs_base.filter(type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE).count()
    nb_occupes   = zs_base.filter(type_zone__in=[
        ZoneSecteur.TYPE_VILLAGE, ZoneSecteur.TYPE_QUARTIER,
        ZoneSecteur.TYPE_SECTEUR_CAMPUS, ZoneSecteur.TYPE_ZONE_ACTIVITE
    ]).count()
    nb_reserves  = zs_base.filter(type_zone=ZoneSecteur.TYPE_ESPACE_RESERVE).count()

    # ── Capacité constructible ────────────────────────────────────────────
    sup_constructible_totale = sup_libre_m2 + (sup_reservee_m2 * 0.5)
    taux_moy_occupation = taux_occupe

    nc_base = NC.objects.all()
    if hasattr(NC, 'zone_secteur') and dossier:
        nc_base = nc_base.filter(zone_secteur__dossier=dossier)

    sup_engagee_nc = nc_base.filter(
        statut__in=NC.STATUTS_ENGAGES
    ).aggregate(t=Sum('superficie_souhaitee'))['t'] or 0
    sup_nette_nc = max(0.0, sup_constructible_totale - sup_engagee_nc)
    pct_engagee_nc = round(sup_engagee_nc / sup_constructible_totale * 100, 1) \
                     if sup_constructible_totale else 0

    # ── Bâtiments / Unités Bâties ──────────────────────────────────────────
    ub_base = UniteBatie.objects.filter(dossier=dossier) if dossier else UniteBatie.objects.all()
    total_batiments  = ub_base.count()
    batiments_actifs = ub_base.filter(statut_occupation=UniteBatie.OCCUPATION_HABITEE).count()
    densite_bat      = round(total_batiments / total_sup_ha, 2) if total_sup_ha else 0

    # ── Pipeline constructions ────────────────────────────────────────────
    nc_stats = {
        item['statut']: {'count': item['count'], 'superficie': item['superficie'] or 0}
        for item in nc_base.values('statut').annotate(
            count=Count('id'), superficie=Sum('superficie_souhaitee')
        )
    }
    total_constructions = nc_base.count()

    _COULEURS_STATUT = {
        'en_cours':  ('#0e7490', '#cffafe'),
        'approuvee': ('#15803d', '#dcfce7'),
        'rejetee':   ('#991b1b', '#fee2e2'),
    }
    pipeline_items = []
    for statut, label in NC.STATUTS:
        info = nc_stats.get(statut, {'count': 0, 'superficie': 0})
        tc, bc = _COULEURS_STATUT.get(statut, ('#374151', '#f3f4f6'))
        pipeline_items.append({
            'statut':    statut, 'label': label,
            'count':     info['count'],
            'superficie': round(info['superficie']),
            'pct': round(info['count'] / total_constructions * 100) if total_constructions else 0,
            'color_text': tc, 'color_bg': bc,
        })

    # Types de construction les plus demandés
    types_demandes = list(nc_base.values('type_construction').annotate(
        count=Count('id'), superficie=Sum('superficie_souhaitee')
    ).order_by('-count')[:8])
    max_count_type = max((t['count'] for t in types_demandes), default=1)
    for t in types_demandes:
        t['pct']       = round(t['count'] / max_count_type * 100) if max_count_type else 0
        t['superficie'] = round(t['superficie'] or 0)

    # ── Historique des travaux ────────────────────────────────────────────
    hc_base = HC.objects.all()
    if hasattr(HC, 'unite_batie') and dossier:
        hc_base = hc_base.filter(unite_batie__dossier=dossier)
    types_travaux_dict = dict(HC.TYPES_TRAVAUX)
    histo_raw = list(
        hc_base
        .annotate(annee=ExtractYear('date_debut'))
        .values('annee', 'type_travaux')
        .annotate(count=Count('id'))
        .order_by('annee')
    )
    for h in histo_raw:
        h['label_travaux'] = types_travaux_dict.get(h['type_travaux'], h['type_travaux'])

    histo_par_annee: dict = {}
    for h in histo_raw:
        a = str(h['annee'])
        histo_par_annee[a] = histo_par_annee.get(a, 0) + h['count']

    histo_chart_labels = list(histo_par_annee.keys())
    histo_chart_data   = list(histo_par_annee.values())

    # ── Charts occupation du sol ──────────────────────────────────────────
    chart_labels = json.dumps([s['label']         for s in stats_enrichis])
    chart_data   = json.dumps([s['superficie_ha'] for s in stats_enrichis])
    chart_colors = json.dumps([s['couleur']       for s in stats_enrichis])

    context = {
        # Globaux
        'total_superficie':    total_sup_ha,
        'total_superficie_m2': round(total_sup_m2),
        'active_dossier':      dossier,
        'total_espaces':       zs_base.count(),
        'total_batiments':     total_batiments,
        'batiments_actifs':    batiments_actifs,
        'densite_bat':         densite_bat,
        # Espaces par type
        'stats_enrichis': stats_enrichis,
        'nb_libres':      nb_libres,
        'nb_occupes':     nb_occupes,
        'nb_reserves':    nb_reserves,
        'taux_libre':     taux_libre,
        'taux_occupe':    taux_occupe,
        'taux_reserve':   taux_reserve,
        'sup_libre_ha':    round(sup_libre_m2    / 10000, 2),
        'sup_occupee_ha':  round(sup_occupee_m2  / 10000, 2),
        'sup_reservee_ha': round(sup_reservee_m2 / 10000, 2),
        # Capacité constructible
        'sup_constructible_totale':    round(sup_constructible_totale),
        'sup_constructible_totale_ha': round(sup_constructible_totale / 10000, 2),
        'taux_moy_occupation':         round(taux_moy_occupation, 1),
        'sup_engagee_nc':              round(sup_engagee_nc),
        'sup_nette_nc':                round(sup_nette_nc),
        'pct_engagee_nc':              pct_engagee_nc,
        # Constructions
        'total_constructions': total_constructions,
        'pipeline_items':      pipeline_items,
        'types_demandes':      types_demandes,
        # Historique
        'historique_stats':   histo_raw,
        'histo_chart_labels': json.dumps(histo_chart_labels),
        'histo_chart_data':   json.dumps(histo_chart_data),
        # Charts
        'chart_labels': chart_labels,
        'chart_data':   chart_data,
        'chart_colors': chart_colors,
    }
    return render(request, 'pdu/statistiques.html', context)
