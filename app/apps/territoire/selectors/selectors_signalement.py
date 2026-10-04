"""
Sélecteurs pour les signalements d'incidents et dommages (SignalementDommage).
Architecture GeenkoDev : requêtes isolées en lecture, annotations et statistiques.
"""

import json
from typing import Optional, Dict, Any
from django.db.models import QuerySet, Q, Count
from django.shortcuts import get_object_or_404
from dossiers.models import SignalementDommage, Dossier


def get_signalements_queryset(
    dossier: Optional[Dossier] = None,
    statut: str = '',
    categorie: str = '',
    priorite: str = '',
    q: str = '',
    sort: str = '-date_signalement',
) -> QuerySet[SignalementDommage]:
    """
    Retourne le queryset des signalements filtré par dossier territorial et critères métier.
    """
    qs = SignalementDommage.objects.select_related('dossier', 'zone_secteur', 'auteur')

    if dossier:
        qs = qs.filter(dossier=dossier)

    if q:
        qs = qs.filter(
            Q(titre__icontains=q) |
            Q(numero__icontains=q) |
            Q(description__icontains=q) |
            Q(zone_secteur__nom__icontains=q)
        )

    if statut:
        qs = qs.filter(statut=statut)

    if categorie:
        qs = qs.filter(categorie=categorie)

    if priorite:
        qs = qs.filter(priorite=priorite)

    return qs.order_by(sort)


def get_signalement_by_id(pk: int, dossier: Optional[Dossier] = None) -> SignalementDommage:
    """Récupère un signalement par son ID avec vérification du dossier."""
    qs = SignalementDommage.objects.select_related('dossier', 'zone_secteur', 'auteur')
    if dossier:
        qs = qs.filter(dossier=dossier)
    return get_object_or_404(qs, pk=pk)


def get_stats_signalements(dossier: Optional[Dossier] = None) -> Dict[str, Any]:
    """Indicateurs statistiques consolidés sur les incidents du territoire."""
    qs = SignalementDommage.objects.all()
    if dossier:
        qs = qs.filter(dossier=dossier)

    agg = qs.aggregate(
        total=Count('id'),
        nouveaux=Count('id', filter=Q(statut=SignalementDommage.STATUT_NOUVEAU)),
        en_cours=Count('id', filter=Q(statut__in=[SignalementDommage.STATUT_PRIS_EN_CHARGE, SignalementDommage.STATUT_EN_COURS])),
        resolus=Count('id', filter=Q(statut=SignalementDommage.STATUT_RESOLU)),
        urgents=Count('id', filter=Q(priorite=SignalementDommage.PRIORITE_URGENTE)),
    )

    total = agg['total'] or 0
    resolus = agg['resolus'] or 0
    taux_resolution = round((resolus / total * 100), 1) if total > 0 else 0.0

    return {
        'total': total,
        'nouveaux': agg['nouveaux'] or 0,
        'en_cours': agg['en_cours'] or 0,
        'resolus': resolus,
        'urgents': agg['urgents'] or 0,
        'taux_resolution_pct': taux_resolution,
    }


def get_signalements_geojson_for_carto(dossier: Optional[Dossier] = None) -> str:
    """Génère un FeatureCollection GeoJSON des points de signalement pour Leaflet."""
    qs = SignalementDommage.objects.select_related('dossier', 'zone_secteur')
    if dossier:
        qs = qs.filter(dossier=dossier)

    features = []
    for s in qs:
        if not s.geometrie:
            continue
        try:
            geom_dict = json.loads(s.geometrie.geojson)
            features.append({
                'type': 'Feature',
                'geometry': geom_dict,
                'properties': {
                    'id': s.pk,
                    'numero': s.numero,
                    'titre': s.titre,
                    'categorie': s.categorie,
                    'categorie_label': s.get_categorie_display(),
                    'priorite': s.priorite,
                    'priorite_label': s.get_priorite_display(),
                    'statut': s.statut,
                    'statut_label': s.get_statut_display(),
                    'date': s.date_signalement.strftime('%d/%m/%Y'),
                    'zone': s.zone_secteur.nom if s.zone_secteur else 'Zone libre',
                }
            })
        except Exception:
            continue

    return json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False)
