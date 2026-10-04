"""
Sélecteurs d'accès aux données pour les subdivisions territoriales (ZoneSecteur).
Architecture GeenkoDev : requêtes isolées en lecture, annotations et filtrages.
"""

import json
from typing import Optional, Dict, Any
from django.db.models import QuerySet, Q, Count, Sum
from django.shortcuts import get_object_or_404
from dossiers.models import ZoneSecteur, Dossier


def get_zones_secteurs_queryset(
    dossier: Optional[Dossier] = None,
    q: str = '',
    type_zone: str = '',
    statut: str = '',
    sort: str = 'nom',
) -> QuerySet[ZoneSecteur]:
    """
    Retourne le queryset ordonné et filtré des subdivisions territoriales (zones/secteurs).
    Si un dossier est fourni, limite rigoureusement au périmètre du workspace territorial.
    """
    qs = ZoneSecteur.objects.select_related('dossier').annotate(
        nb_unites_baties=Count('unites_baties'),
        surface_batie_m2=Sum('unites_baties__superficie_m2'),
    )

    if dossier:
        qs = qs.filter(dossier=dossier)

    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q) | Q(responsable_nom__icontains=q))

    if type_zone:
        qs = qs.filter(type_zone=type_zone)

    if statut:
        qs = qs.filter(statut=statut)

    valid_sorts = {
        'nom', '-nom', 'code', '-code',
        'superficie_m2', '-superficie_m2',
        'nb_unites_baties', '-nb_unites_baties',
        'date_creation', '-date_creation',
    }
    return qs.order_by(sort if sort in valid_sorts else 'nom')


def get_zone_secteur_by_id(pk: int, dossier: Optional[Dossier] = None) -> ZoneSecteur:
    """Récupère une subdivision territoriale par sa clé primaire, avec vérification du dossier."""
    qs = ZoneSecteur.objects.select_related('dossier')
    if dossier:
        qs = qs.filter(dossier=dossier)
    return get_object_or_404(qs, pk=pk)


def get_zone_stats(zone: ZoneSecteur) -> Dict[str, Any]:
    """Calcule les indicateurs clés et l'occupation du sol pour une zone donnée."""
    from dossiers.models import UniteBatie

    batiments = zone.unites_baties.all()
    agg = batiments.aggregate(
        total=Count('id'),
        occupes=Count('id', filter=Q(statut_occupation=UniteBatie.OCCUPATION_HABITEE)),
        vacants=Count('id', filter=Q(statut_occupation=UniteBatie.OCCUPATION_VACANT)),
        surface_batie=Sum('superficie_m2'),
    )

    total_bat = agg['total'] or 0
    surface_batie = round(agg['surface_batie'] or 0.0, 2)
    superficie_zone = zone.superficie_m2 or 0.0

    taux_emprise = round((surface_batie / superficie_zone * 100), 2) if superficie_zone > 0 else 0.0

    return {
        'total_unites_baties': total_bat,
        'nb_occupes': agg['occupes'] or 0,
        'nb_vacants': agg['vacants'] or 0,
        'surface_batie_m2': surface_batie,
        'taux_emprise_pct': taux_emprise,
        'superficie_ha': zone.superficie_ha or (round(superficie_zone / 10000, 2) if superficie_zone else 0.0),
    }


def get_zones_geojson_for_carto(dossier: Optional[Dossier] = None) -> str:
    """Génère un FeatureCollection GeoJSON des zones pour injection directe dans Leaflet."""
    qs = ZoneSecteur.objects.select_related('dossier')
    if dossier:
        qs = qs.filter(dossier=dossier)

    features = []
    for z in qs.order_by('nom'):
        if not z.geometrie:
            continue
        try:
            geom_dict = json.loads(z.geometrie.geojson)
            features.append({
                'type': 'Feature',
                'geometry': geom_dict,
                'properties': {
                    'id': z.pk,
                    'code': z.code,
                    'nom': z.nom,
                    'type_zone': z.type_zone,
                    'type_label': z.get_type_zone_display(),
                    'superficie_m2': z.superficie_m2,
                    'superficie_ha': z.superficie_ha,
                    'dossier_nom': z.dossier.nom if z.dossier else '',
                }
            })
        except Exception:
            continue

    return json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False)
