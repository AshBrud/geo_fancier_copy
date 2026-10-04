"""
Sélecteurs d'accès aux données pour les réseaux linéaires et voiries (ReseauLineaire).
Architecture GeenkoDev : requêtes isolées en lecture, annotations et filtrages.
"""

import json
from typing import Optional, Dict, Any
from django.db.models import QuerySet, Q, Count, Sum
from django.shortcuts import get_object_or_404
from dossiers.models import ReseauLineaire, Dossier


def get_reseaux_lineaires_queryset(
    dossier: Optional[Dossier] = None,
    q: str = '',
    type_voie: str = '',
    sort: str = 'nom',
) -> QuerySet[ReseauLineaire]:
    """
    Retourne le queryset ordonné et filtré des voies et linéaires du territoire.
    """
    qs = ReseauLineaire.objects.select_related('dossier')

    if dossier:
        qs = qs.filter(dossier=dossier)

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(code__icontains=q) |
            Q(etat_chaussee__icontains=q)
        )

    if type_voie:
        qs = qs.filter(type_voie=type_voie)

    valid_sorts = {
        'nom', '-nom',
        'code', '-code',
        'type_voie', '-type_voie',
        'longueur_metres', '-longueur_metres',
        'date_creation', '-date_creation',
    }
    return qs.order_by(sort if sort in valid_sorts else 'nom')


def get_reseau_lineaire_by_id(pk: int, dossier: Optional[Dossier] = None) -> ReseauLineaire:
    """Récupère un tronçon linéaire par sa clé primaire avec vérification du dossier."""
    qs = ReseauLineaire.objects.select_related('dossier')
    if dossier:
        qs = qs.filter(dossier=dossier)
    return get_object_or_404(qs, pk=pk)


def get_reseaux_lineaires_stats(dossier: Optional[Dossier] = None) -> Dict[str, Any]:
    """Calcule le linéaire total, la répartition par type et le nombre de tronçons."""
    qs = ReseauLineaire.objects.all()
    if dossier:
        qs = qs.filter(dossier=dossier)

    agg = qs.aggregate(
        total_troncons=Count('id'),
        longueur_totale_m=Sum('longueur_metres'),
    )

    total_m = agg['longueur_totale_m'] or 0.0
    total_km = round(total_m / 1000, 2)

    return {
        'total_troncons': agg['total_troncons'] or 0,
        'longueur_totale_m': round(total_m, 1),
        'longueur_totale_km': total_km,
    }


def get_reseaux_lineaires_geojson_for_carto(dossier: Optional[Dossier] = None) -> str:
    """Génère un FeatureCollection GeoJSON pour projection cartographique sur Leaflet."""
    qs = ReseauLineaire.objects.select_related('dossier')
    if dossier:
        qs = qs.filter(dossier=dossier)

    features = []
    for r in qs:
        if not r.geometrie:
            continue
        try:
            geom_dict = json.loads(r.geometrie.geojson)
            features.append({
                'type': 'Feature',
                'geometry': geom_dict,
                'properties': {
                    'id': r.pk,
                    'code': r.code,
                    'nom': r.nom or r.get_type_voie_display(),
                    'type_voie': r.type_voie,
                    'type_label': r.get_type_voie_display(),
                    'couleur': r.couleur,
                    'longueur_m': r.longueur_metres,
                    'longueur_km': r.longueur_km,
                    'largeur_m': r.largeur_estimee_m,
                    'etat': r.etat_chaussee or 'Non renseigné',
                }
            })
        except Exception:
            continue

    return json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False)
