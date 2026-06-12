from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from foncier.models import Espace, Batiment
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
    total_superficie = Espace.objects.aggregate(t=Sum('superficie'))['t'] or 1

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
    espaces_stats = Espace.objects.values('type_espace').annotate(
        count=Count('id'), superficie=Sum('superficie')
    )
    total_sup = Espace.objects.aggregate(t=Sum('superficie'))['t'] or 0

    from django.db.models.functions import ExtractYear
    histo = (
        HistoriqueConstruction.objects
        .annotate(annee=ExtractYear('date_debut'))
        .values('annee', 'type_travaux')
        .annotate(count=Count('id'))
        .order_by('annee')
    )

    context = {
        'espaces_stats': list(espaces_stats),
        'total_superficie': round(total_sup / 10000, 2),
        'total_batiments': Batiment.objects.count(),
        'total_espaces': Espace.objects.count(),
        'historique_stats': list(histo),
        'types_espaces': Espace.TYPES,
        'couleurs_espaces': Espace.COULEURS,
    }
    return render(request, 'pdu/statistiques.html', context)
