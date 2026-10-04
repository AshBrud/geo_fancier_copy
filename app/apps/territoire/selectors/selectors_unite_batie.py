"""
Sélecteurs d'accès aux données pour le recensement bâti unifié (UniteBatie).
Architecture GeenkoDev : requêtes isolées en lecture, annotations et filtrages.
"""

import json
from typing import Optional, Dict, Any
from django.db.models import QuerySet, Q, Count, Sum, Avg
from django.shortcuts import get_object_or_404
from dossiers.models import UniteBatie, Dossier, ZoneSecteur


def get_unites_baties_queryset(
    dossier: Optional[Dossier] = None,
    q: str = '',
    type_bati: str = '',
    statut_occupation: str = '',
    zone_id: Optional[int] = None,
    sort: str = 'code',
) -> QuerySet[UniteBatie]:
    """
    Retourne le queryset ordonné et filtré des unités bâties.
    Filtre strictement par le dossier actif du workspace territorial.
    """
    qs = UniteBatie.objects.select_related('dossier', 'zone_secteur')

    if dossier:
        qs = qs.filter(dossier=dossier)

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(code__icontains=q) |
            Q(zone_secteur__nom__icontains=q)
        )

    if type_bati:
        qs = qs.filter(type_bati=type_bati)

    if statut_occupation:
        qs = qs.filter(statut_occupation=statut_occupation)

    if zone_id:
        qs = qs.filter(zone_secteur_id=zone_id)

    valid_sorts = {
        'code', '-code',
        'nom', '-nom',
        'superficie_m2', '-superficie_m2',
        'etages', '-etages',
        'date_creation', '-date_creation',
    }
    return qs.order_by(sort if sort in valid_sorts else 'code')


def get_unite_batie_by_id(pk: int, dossier: Optional[Dossier] = None) -> UniteBatie:
    """Récupère une unité bâtie par sa clé primaire, avec vérification du dossier."""
    qs = UniteBatie.objects.select_related('dossier', 'zone_secteur')
    if dossier:
        qs = qs.filter(dossier=dossier)
    return get_object_or_404(qs, pk=pk)


def get_unites_baties_stats(dossier: Optional[Dossier] = None) -> Dict[str, Any]:
    """Calcule les indicateurs statistiques consolidés du bâti pour le dossier."""
    qs = UniteBatie.objects.all()
    if dossier:
        qs = qs.filter(dossier=dossier)

    agg = qs.aggregate(
        total=Count('id'),
        occupes=Count('id', filter=Q(statut_occupation=UniteBatie.OCCUPATION_HABITEE)),
        vacants=Count('id', filter=Q(statut_occupation=UniteBatie.OCCUPATION_VACANT)),
        en_construction=Count('id', filter=Q(statut_occupation=UniteBatie.OCCUPATION_EN_CONSTRUCTION)),
        ruines=Count('id', filter=Q(statut_occupation=UniteBatie.OCCUPATION_RUINE)),
        surface_totale=Sum('superficie_m2'),
        surface_moyenne=Avg('superficie_m2'),
    )

    total = agg['total'] or 0
    surface_totale = round(agg['surface_totale'] or 0.0, 2)
    surface_moyenne = round(agg['surface_moyenne'] or 0.0, 1)

    taux_occupation = round((agg['occupes'] / total * 100), 1) if total > 0 else 0.0

    return {
        'total': total,
        'nb_occupes': agg['occupes'] or 0,
        'nb_vacants': agg['vacants'] or 0,
        'nb_en_construction': agg['en_construction'] or 0,
        'nb_ruines': agg['ruines'] or 0,
        'surface_totale_m2': surface_totale,
        'surface_moyenne_m2': surface_moyenne,
        'taux_occupation_pct': taux_occupation,
    }


def get_unites_baties_geojson_for_carto(
    dossier: Optional[Dossier] = None,
    zone_id: Optional[int] = None
) -> str:
    """Génère un FeatureCollection GeoJSON pour projection cartographique directe."""
    qs = UniteBatie.objects.select_related('dossier', 'zone_secteur')
    if dossier:
        qs = qs.filter(dossier=dossier)
    if zone_id:
        qs = qs.filter(zone_secteur_id=zone_id)

    features = []
    for bat in qs:
        if not bat.geometrie:
            continue
        try:
            geom_dict = json.loads(bat.geometrie.geojson)
            features.append({
                'type': 'Feature',
                'geometry': geom_dict,
                'properties': {
                    'id': bat.pk,
                    'code': bat.code,
                    'nom': bat.nom or bat.get_type_bati_display(),
                    'type_bati': bat.type_bati,
                    'type_label': bat.get_type_bati_display(),
                    'statut_occupation': bat.statut_occupation,
                    'statut_label': bat.get_statut_occupation_display(),
                    'couleur': bat.couleur_statut,
                    'superficie_m2': bat.superficie_m2,
                    'etages': bat.etages,
                    'zone_nom': bat.zone_secteur.nom if bat.zone_secteur else 'Zone libre',
                }
            })
        except Exception:
            continue

    return json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False)
