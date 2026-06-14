from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from foncier.models import Espace, Batiment, SUPERFICIE_CAMPUS_M2
from constructions.models import HistoriqueConstruction
from accounts.decorators import foncier_required
import json


@login_required
@foncier_required
def aide_pdu(request):
    # Analyse de l'occupation du sol
    espaces_par_type = Espace.objects.values('type_espace').annotate(
        count=Count('id'), superficie=Sum('superficie')
    )
    total_superficie = SUPERFICIE_CAMPUS_M2  # superficie officielle campus UAD

    occupation = []
    for e in espaces_par_type:
        pct = round((e['superficie'] or 0) / total_superficie * 100, 1)
        occupation.append({
            'type': dict(Espace.TYPES).get(e['type_espace'], e['type_espace']),
            'type_key': e['type_espace'],
            'count': e['count'],
            'superficie': round((e['superficie'] or 0) / 10000, 2),
            'pourcentage': pct,
            'couleur': Espace.COULEURS.get(e['type_espace'], '#ccc'),
        })

    zones_constructibles = Espace.objects.filter(type_espace=Espace.TYPE_LIBRE)
    superficie_constructible = zones_constructibles.aggregate(t=Sum('superficie'))['t'] or 0

    # Recommandations basées sur les données
    recommandations = []
    taux_libre = (superficie_constructible / total_superficie * 100) if total_superficie else 0

    if taux_libre > 30:
        recommandations.append({
            'niveau': 'success',
            'titre': 'Potentiel de développement élevé',
            'texte': f'{taux_libre:.1f}% du campus est libre, offrant un bon potentiel pour de nouveaux aménagements.',
        })
    elif taux_libre > 10:
        recommandations.append({
            'niveau': 'warning',
            'titre': 'Potentiel de développement limité',
            'texte': f'Seulement {taux_libre:.1f}% du campus est libre. Planifier soigneusement les nouvelles constructions.',
        })
    else:
        recommandations.append({
            'niveau': 'danger',
            'titre': 'Saturation foncière',
            'texte': f'Le campus est occupé à {100 - taux_libre:.1f}%. La rénovation et densification verticale sont recommandées.',
        })

    if zones_constructibles.count() > 0:
        recommandations.append({
            'niveau': 'info',
            'titre': 'Zones constructibles identifiées',
            'texte': f'{zones_constructibles.count()} zones libres disponibles pour une superficie totale de {superficie_constructible / 10000:.2f} ha.',
        })

    # Graphique répartition pour PDU
    chart_data = [round((e['superficie'] or 0) / 10000, 2) for e in espaces_par_type]
    chart_labels = [dict(Espace.TYPES).get(e['type_espace'], e['type_espace']) for e in espaces_par_type]
    chart_colors = [Espace.COULEURS.get(e['type_espace'], '#ccc') for e in espaces_par_type]

    context = {
        'occupation': occupation,
        'zones_constructibles': zones_constructibles,
        'superficie_constructible': round(superficie_constructible / 10000, 2),
        'total_superficie': round(total_superficie / 10000, 2),
        'taux_libre': round(taux_libre, 1),
        'recommandations': recommandations,
        'nb_batiments': Batiment.objects.count(),
        'chart_data': json.dumps(chart_data),
        'chart_labels': json.dumps(chart_labels),
        'chart_colors': json.dumps(chart_colors),
    }
    return render(request, 'pdu/aide_pdu.html', context)


@login_required
@foncier_required
def statistiques(request):
    from django.db.models.functions import ExtractYear
    from constructions.models import HistoriqueConstruction as HC

    # Données brutes espaces
    espaces_raw = Espace.objects.values('type_espace').annotate(
        count=Count('id'), superficie=Sum('superficie')
    )
    total_sup_m2 = SUPERFICIE_CAMPUS_M2  # superficie officielle campus UAD
    total_sup_ha = round(total_sup_m2 / 10000, 2)

    # Stats enrichies (superficie en ha + pourcentage corrects)
    stats_enrichis = []
    for item in espaces_raw:
        sup_ha = round((item['superficie'] or 0) / 10000, 2)
        pct = round((item['superficie'] or 0) / total_sup_m2 * 100, 1) if total_sup_m2 else 0
        stats_enrichis.append({
            'type_espace': item['type_espace'],
            'label': dict(Espace.TYPES).get(item['type_espace'], item['type_espace']),
            'couleur': Espace.COULEURS.get(item['type_espace'], '#94a3b8'),
            'count': item['count'],
            'superficie_ha': sup_ha,
            'pourcentage': pct,
        })
    stats_enrichis.sort(key=lambda x: x['superficie_ha'], reverse=True)

    # Taux libre / occupé
    sup_libre_m2 = Espace.objects.filter(
        type_espace=Espace.TYPE_LIBRE).aggregate(s=Sum('superficie'))['s'] or 0
    taux_libre = round(sup_libre_m2 / total_sup_m2 * 100, 1)

    # Historique travaux
    types_travaux_dict = dict(HC.TYPES_TRAVAUX)
    histo = list(
        HC.objects
        .annotate(annee=ExtractYear('date_debut'))
        .values('annee', 'type_travaux')
        .annotate(count=Count('id'))
        .order_by('annee')
    )
    for h in histo:
        h['label_travaux'] = types_travaux_dict.get(h['type_travaux'], h['type_travaux'])

    context = {
        'stats_enrichis': stats_enrichis,
        'total_superficie': total_sup_ha,
        'total_batiments': Batiment.objects.count(),
        'total_espaces': Espace.objects.count(),
        'nb_espaces_libres': Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count(),
        'taux_libre': taux_libre,
        'taux_occupe': round(100 - taux_libre, 1),
        'historique_stats': histo,
        'chart_labels': json.dumps([s['label'] for s in stats_enrichis]),
        'chart_data': json.dumps([s['superficie_ha'] for s in stats_enrichis]),
        'chart_colors': json.dumps([s['couleur'] for s in stats_enrichis]),
    }
    return render(request, 'pdu/statistiques.html', context)
