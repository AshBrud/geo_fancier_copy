from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from foncier.models import Espace, Batiment, SUPERFICIE_CAMPUS_M2
from constructions.models import NouvelleConstruction, HistoriqueConstruction
from accounts.decorators import foncier_required
import json


def _pks_constructions_espace(espace, statuts):
    """PKs des constructions (dans les statuts donnés) concernant cet espace."""
    q = NouvelleConstruction.objects.filter(statut__in=statuts)
    pks = set(q.filter(espace_souhaitee=espace).values_list('pk', flat=True))
    if espace.geometrie:
        pks.update(q.filter(
            zone_souhaitee__isnull=False,
            zone_souhaitee__intersects=espace.geometrie,
        ).values_list('pk', flat=True))
    return pks


def _sup(pks):
    """Superficie totale d'un ensemble de constructions (par PKs)."""
    if not pks:
        return 0.0
    return NouvelleConstruction.objects.filter(pk__in=pks).aggregate(
        t=Sum('superficie_souhaitee')
    )['t'] or 0.0


@login_required
@foncier_required
def aide_pdu(request):

    # ── 1. Analyse par espace ──────────────────────────────────────────────
    espaces_actifs = list(Espace.objects.filter(
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE]
    ).order_by('nom'))

    espaces_stats = []
    sup_constructible_totale = 0.0
    sup_engagee_totale       = 0.0
    sup_attente_totale       = 0.0

    for espace in espaces_actifs:
        sup_brute        = espace.superficie or 0.0
        sup_constructible = sup_brute * (espace.taux_occupation / 100)

        pks_eng  = _pks_constructions_espace(espace, NouvelleConstruction.STATUTS_ENGAGES)
        pks_att  = _pks_constructions_espace(espace, [NouvelleConstruction.STATUT_ATTENTE])
        sup_eng  = _sup(pks_eng)
        sup_att  = _sup(pks_att)
        sup_nette = max(0.0, sup_constructible - sup_eng)
        pct_utilise = round(sup_eng / sup_constructible * 100, 1) if sup_constructible else 0.0

        if pct_utilise >= 80:
            niveau = 'danger'
        elif pct_utilise >= 50:
            niveau = 'warning'
        else:
            niveau = 'success'

        espaces_stats.append({
            'espace':          espace,
            'sup_brute':       round(sup_brute),
            'sup_constructible': round(sup_constructible),
            'sup_engagee':     round(sup_eng),
            'sup_attente':     round(sup_att),
            'sup_nette':       round(sup_nette),
            'pct_utilise':     pct_utilise,
            'pct_nette':       round(max(0, 100 - pct_utilise), 1),
            'niveau':          niveau,
            'nb_engagees':     len(pks_eng),
            'nb_attente':      len(pks_att),
            'attente_depasse': sup_att > sup_nette,
        })

        sup_constructible_totale += sup_constructible
        sup_engagee_totale       += sup_eng
        sup_attente_totale       += sup_att

    espaces_stats.sort(key=lambda x: x['sup_nette'], reverse=True)

    sup_nette_totale = max(0.0, sup_constructible_totale - sup_engagee_totale)
    pct_engagement   = round(sup_engagee_totale / sup_constructible_totale * 100, 1) \
                       if sup_constructible_totale else 0.0
    pct_nette        = round(sup_nette_totale / sup_constructible_totale * 100, 1) \
                       if sup_constructible_totale else 0.0

    # ── 2. Pipeline constructions ─────────────────────────────────────────
    def _nb(statut):
        return NouvelleConstruction.objects.filter(statut=statut).count()

    def _sup_statut(statut):
        return NouvelleConstruction.objects.filter(statut=statut).aggregate(
            t=Sum('superficie_souhaitee'))['t'] or 0.0

    nb_attente    = _nb(NouvelleConstruction.STATUT_ATTENTE)
    nb_approuvees = _nb(NouvelleConstruction.STATUT_APPROUVE)
    nb_en_cours   = _nb(NouvelleConstruction.STATUT_EN_COURS)
    nb_terminees  = _nb(NouvelleConstruction.STATUT_TERMINE)

    sup_att_global  = _sup_statut(NouvelleConstruction.STATUT_ATTENTE)
    sup_app_global  = _sup_statut(NouvelleConstruction.STATUT_APPROUVE)
    sup_enc_global  = _sup_statut(NouvelleConstruction.STATUT_EN_COURS)
    sup_ter_global  = _sup_statut(NouvelleConstruction.STATUT_TERMINE)

    # ── 3. Scénario : si toutes les demandes en attente approuvées ────────
    sup_scenario      = sup_engagee_totale + sup_att_global
    sup_nette_scenario = max(0.0, sup_constructible_totale - sup_scenario)
    pct_scenario      = round(sup_scenario / sup_constructible_totale * 100, 1) \
                        if sup_constructible_totale else 0.0
    scenario_faisable = sup_att_global <= sup_nette_totale

    # ── 4. Score de planification ─────────────────────────────────────────
    score = 100

    if pct_nette < 10:      score -= 40
    elif pct_nette < 25:    score -= 22
    elif pct_nette < 50:    score -= 10

    if nb_attente > 0 and sup_nette_totale >= 0:
        ratio = sup_att_global / max(sup_nette_totale, 1)
        if ratio > 2:   score -= 25
        elif ratio > 1: score -= 15
        elif ratio > .5: score -= 6

    nb_zones_saturees = sum(1 for e in espaces_stats if e['pct_utilise'] >= 80)
    score -= min(15, nb_zones_saturees * 8)

    score = max(0, min(100, round(score)))
    if score < 40:    score_niveau, score_label = 'danger',  'Critique'
    elif score < 70:  score_niveau, score_label = 'warning', 'Modéré'
    else:             score_niveau, score_label = 'success', 'Satisfaisant'

    # ── 5. Recommandations intelligentes ─────────────────────────────────
    recommandations = []

    # A. Capacité globale
    if pct_nette < 10:
        recommandations.append({
            'priorite': 1, 'niveau': 'danger',
            'categorie': 'Capacité foncière',
            'icone': 'exclamation-octagon-fill',
            'titre': 'Capacité constructible critique',
            'texte': (
                f"Il ne reste que {sup_nette_totale:,.0f} m² constructibles nets "
                f"({pct_nette}% de la capacité totale). Le campus approche de la saturation."
            ),
            'actions': [
                "Étudier la densification verticale (construction en hauteur)",
                "Réviser les taux d'occupation des espaces sous-utilisés",
                "Envisager l'extension du périmètre foncier du campus",
            ],
        })
    elif pct_nette < 30:
        recommandations.append({
            'priorite': 2, 'niveau': 'warning',
            'categorie': 'Capacité foncière',
            'icone': 'exclamation-triangle-fill',
            'titre': 'Capacité constructible limitée',
            'texte': (
                f"{sup_nette_totale:,.0f} m² constructibles nets restants ({pct_nette}%). "
                "Prioriser les projets à fort impact avant saturation."
            ),
            'actions': [
                "Réserver la capacité restante aux projets stratégiques (amphis, labo)",
                "Planifier un schéma d'aménagement directeur à 5 ans",
            ],
        })
    else:
        recommandations.append({
            'priorite': 4, 'niveau': 'success',
            'categorie': 'Capacité foncière',
            'icone': 'check-circle-fill',
            'titre': 'Bonne capacité de développement',
            'texte': (
                f"{sup_nette_totale:,.0f} m² constructibles nets disponibles ({pct_nette}%). "
                "Le campus dispose d'une marge de développement satisfaisante."
            ),
            'actions': [
                "Planifier les projets à moyen terme selon le PDU",
                "Maintenir des réserves foncières pour les besoins futurs",
            ],
        })

    # B. Zones saturées
    if nb_zones_saturees > 0:
        noms = ', '.join(
            f"« {e['espace'].nom} »" for e in espaces_stats if e['pct_utilise'] >= 80
        )
        recommandations.append({
            'priorite': 2, 'niveau': 'danger',
            'categorie': 'Zones saturées',
            'icone': 'geo-fill',
            'titre': f"{nb_zones_saturees} zone(s) en saturation constructible (≥ 80%)",
            'texte': f"Zones concernées : {noms}. "
                     "Plus de 80% de la superficie constructible est déjà engagée.",
            'actions': [
                "Ne plus accepter de nouvelles constructions dans ces zones",
                "Rediriger les nouvelles demandes vers les zones disponibles",
            ],
        })

    # C. Pipeline de demandes
    if nb_attente > 0:
        if not scenario_faisable:
            recommandations.append({
                'priorite': 1, 'niveau': 'danger',
                'categorie': 'Pipeline',
                'icone': 'clipboard2-x-fill',
                'titre': 'Demandes en attente supérieures à la capacité disponible',
                'texte': (
                    f"{nb_attente} demande(s) en attente totalisent {sup_att_global:,.0f} m², "
                    f"mais seulement {sup_nette_totale:,.0f} m² nets sont disponibles. "
                    "Toutes les demandes ne peuvent pas être satisfaites."
                ),
                'actions': [
                    "Prioriser selon les besoins pédagogiques et stratégiques",
                    "Constituer une commission de priorisation des projets",
                    "Rejeter ou reporter les demandes non prioritaires",
                ],
            })
        else:
            recommandations.append({
                'priorite': 3, 'niveau': 'info',
                'categorie': 'Pipeline',
                'icone': 'clipboard2-check-fill',
                'titre': f"{nb_attente} demande(s) en attente — réalisables",
                'texte': (
                    f"Les {nb_attente} demande(s) ({sup_att_global:,.0f} m² total) "
                    f"peuvent être satisfaites dans la capacité disponible "
                    f"({sup_nette_totale:,.0f} m² nets)."
                ),
                'actions': [
                    "Instruire les demandes en attente prioritairement",
                    "Vérifier la compatibilité avec le zonage avant approbation",
                ],
            })

    # D. Zones prioritaires pour développement
    zones_ok = [e for e in espaces_stats if e['sup_nette'] > 100]
    if zones_ok:
        meilleure = zones_ok[0]
        recommandations.append({
            'priorite': 3, 'niveau': 'info',
            'categorie': 'Zone prioritaire',
            'icone': 'star-fill',
            'titre': f"Zone prioritaire : « {meilleure['espace'].nom} »",
            'texte': (
                f"Capacité nette disponible la plus élevée : {meilleure['sup_nette']:,} m² "
                f"({meilleure['espace'].taux_occupation:.0f}% constructibles, "
                f"{meilleure['pct_nette']}% encore libre)."
            ),
            'actions': [
                f"Orienter les nouvelles demandes vers la zone « {meilleure['espace'].nom} »",
                "Préparer un plan masse d'aménagement pour cette zone",
            ],
        })

    # E. Conflits demandes/capacité par zone
    zones_conflit = [e for e in espaces_stats if e['attente_depasse']]
    if zones_conflit:
        recommandations.append({
            'priorite': 2, 'niveau': 'warning',
            'categorie': 'Conflits zonaux',
            'icone': 'exclamation-diamond-fill',
            'titre': f"{len(zones_conflit)} zone(s) avec demandes dépassant la capacité nette",
            'texte': (
                f"Dans {len(zones_conflit)} zone(s), les demandes en attente dépassent "
                "la superficie nette disponible. Des arbitrages seront nécessaires."
            ),
            'actions': [
                "Analyser zone par zone les demandes conflictuelles",
                "Appliquer le principe du premier arrivé ou d'une commission d'arbitrage",
            ],
        })

    recommandations.sort(key=lambda r: r['priorite'])

    # ── 6. Occupation générale (pour chart) ───────────────────────────────
    espaces_par_type = Espace.objects.values('type_espace').annotate(
        count=Count('id'), superficie=Sum('superficie')
    )
    occupation = []
    for e in espaces_par_type:
        pct = round((e['superficie'] or 0) / SUPERFICIE_CAMPUS_M2 * 100, 1)
        occupation.append({
            'type':       dict(Espace.TYPES).get(e['type_espace'], e['type_espace']),
            'type_key':   e['type_espace'],
            'count':      e['count'],
            'superficie': round((e['superficie'] or 0) / 10000, 2),
            'pourcentage': pct,
            'couleur':    Espace.COULEURS.get(e['type_espace'], '#ccc'),
        })

    chart_data   = [round((e['superficie'] or 0) / 10000, 2) for e in espaces_par_type]
    chart_labels = [dict(Espace.TYPES).get(e['type_espace'], e['type_espace']) for e in espaces_par_type]
    chart_colors = [Espace.COULEURS.get(e['type_espace'], '#ccc') for e in espaces_par_type]

    context = {
        # Score global
        'score':        score,
        'score_niveau': score_niveau,
        'score_label':  score_label,
        # KPIs globaux
        'total_superficie':           round(SUPERFICIE_CAMPUS_M2 / 10000, 2),
        'sup_constructible_totale':   round(sup_constructible_totale),
        'sup_constructible_totale_ha': round(sup_constructible_totale / 10000, 2),
        'sup_engagee_totale':         round(sup_engagee_totale),
        'sup_nette_totale':           round(sup_nette_totale),
        'sup_nette_totale_ha':        round(sup_nette_totale / 10000, 2),
        'pct_engagement':             pct_engagement,
        'pct_nette':                  pct_nette,
        # Pipeline
        'nb_attente':    nb_attente,
        'nb_approuvees': nb_approuvees,
        'nb_en_cours':   nb_en_cours,
        'nb_terminees':  nb_terminees,
        'sup_att_global': round(sup_att_global),
        'sup_app_global': round(sup_app_global),
        'sup_enc_global': round(sup_enc_global),
        'sup_ter_global': round(sup_ter_global),
        # Scénario
        'pct_scenario':       pct_scenario,
        'sup_nette_scenario': round(sup_nette_scenario),
        'scenario_faisable':  scenario_faisable,
        # Zones
        'espaces_stats':     espaces_stats,
        'nb_zones_saturees': nb_zones_saturees,
        # Recommandations
        'recommandations': recommandations,
        # Occupation + charts
        'occupation':   occupation,
        'nb_batiments': Batiment.objects.count(),
        'chart_data':   json.dumps(chart_data),
        'chart_labels': json.dumps(chart_labels),
        'chart_colors': json.dumps(chart_colors),
    }
    return render(request, 'pdu/aide_pdu.html', context)


@login_required
@foncier_required
def statistiques(request):
    from django.db.models.functions import ExtractYear
    from constructions.models import HistoriqueConstruction as HC, NouvelleConstruction as NC

    total_sup_m2 = SUPERFICIE_CAMPUS_M2
    total_sup_ha = round(total_sup_m2 / 10000, 2)

    # ── Espaces par type ──────────────────────────────────────────────────
    espaces_raw = Espace.objects.values('type_espace').annotate(
        count=Count('id'), superficie=Sum('superficie')
    )
    stats_enrichis = []
    for item in espaces_raw:
        sup_ha = round((item['superficie'] or 0) / 10000, 2)
        pct = round((item['superficie'] or 0) / total_sup_m2 * 100, 1) if total_sup_m2 else 0
        stats_enrichis.append({
            'type_espace':   item['type_espace'],
            'label':         dict(Espace.TYPES).get(item['type_espace'], item['type_espace']),
            'couleur':       Espace.COULEURS.get(item['type_espace'], '#94a3b8'),
            'count':         item['count'],
            'superficie_ha': sup_ha,
            'pourcentage':   pct,
        })
    stats_enrichis.sort(key=lambda x: x['superficie_ha'], reverse=True)

    def _sup_type(t):
        return Espace.objects.filter(type_espace=t).aggregate(s=Sum('superficie'))['s'] or 0

    sup_libre_m2    = _sup_type(Espace.TYPE_LIBRE)
    sup_occupee_m2  = _sup_type(Espace.TYPE_OCCUPE)
    sup_reservee_m2 = _sup_type(Espace.TYPE_RESERVE)
    taux_libre   = round(sup_libre_m2    / total_sup_m2 * 100, 1) if total_sup_m2 else 0
    taux_occupe  = round(sup_occupee_m2  / total_sup_m2 * 100, 1) if total_sup_m2 else 0
    taux_reserve = round(sup_reservee_m2 / total_sup_m2 * 100, 1) if total_sup_m2 else 0
    nb_libres    = Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count()
    nb_occupes   = Espace.objects.filter(type_espace=Espace.TYPE_OCCUPE).count()
    nb_reserves  = Espace.objects.filter(type_espace=Espace.TYPE_RESERVE).count()

    # ── Capacité constructible ────────────────────────────────────────────
    espaces_actifs = list(Espace.objects.filter(
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE]
    ))
    sup_constructible_totale = sum(
        (e.superficie or 0) * (e.taux_occupation / 100) for e in espaces_actifs
    )
    taux_moy_occupation = (
        sum(e.taux_occupation for e in espaces_actifs) / len(espaces_actifs)
        if espaces_actifs else 0
    )
    sup_engagee_nc = NC.objects.filter(
        statut__in=NC.STATUTS_ENGAGES
    ).aggregate(t=Sum('superficie_souhaitee'))['t'] or 0
    sup_nette_nc = max(0.0, sup_constructible_totale - sup_engagee_nc)
    pct_engagee_nc = round(sup_engagee_nc / sup_constructible_totale * 100, 1) \
                     if sup_constructible_totale else 0

    # ── Bâtiments ─────────────────────────────────────────────────────────
    total_batiments  = Batiment.objects.count()
    batiments_actifs = Batiment.objects.filter(est_actif=True).count()
    densite_bat      = round(total_batiments / total_sup_ha, 2) if total_sup_ha else 0

    # ── Pipeline constructions ────────────────────────────────────────────
    nc_stats = {
        item['statut']: {'count': item['count'], 'superficie': item['superficie'] or 0}
        for item in NC.objects.values('statut').annotate(
            count=Count('id'), superficie=Sum('superficie_souhaitee')
        )
    }
    total_constructions = NC.objects.count()

    _COULEURS_STATUT = {
        'attente':   ('#7c3aed', '#ede9fe'),
        'approuvee': ('#15803d', '#dcfce7'),
        'en_cours':  ('#0e7490', '#cffafe'),
        'terminee':  ('#374151', '#f3f4f6'),
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
    types_demandes = list(NC.objects.values('type_construction').annotate(
        count=Count('id'), superficie=Sum('superficie_souhaitee')
    ).order_by('-count')[:8])
    max_count_type = max((t['count'] for t in types_demandes), default=1)
    for t in types_demandes:
        t['pct']       = round(t['count'] / max_count_type * 100) if max_count_type else 0
        t['superficie'] = round(t['superficie'] or 0)

    # ── Historique des travaux ────────────────────────────────────────────
    types_travaux_dict = dict(HC.TYPES_TRAVAUX)
    histo_raw = list(
        HC.objects
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
        'total_superficie': total_sup_ha,
        'total_espaces':    Espace.objects.count(),
        'total_batiments':  total_batiments,
        'batiments_actifs': batiments_actifs,
        'densite_bat':      densite_bat,
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
