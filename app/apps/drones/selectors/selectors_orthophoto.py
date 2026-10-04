import json
from django.shortcuts import get_object_or_404

from ..models import Orthophoto


def get_orthophotos_queryset(dossier=None, valide_only=False):
    """Queryset filtrable pour les orthophotos."""
    qs = Orthophoto.objects.select_related('mission', 'validateur')
    if dossier:
        qs = qs.filter(dossier=dossier)
    if valide_only:
        qs = qs.filter(valide=True)
    return qs.order_by('-date_prise')


def get_orthophoto_by_id(pk):
    """Récupère une orthophoto par sa clé primaire."""
    return get_object_or_404(Orthophoto.objects.select_related('mission', 'validateur'), pk=pk)


def get_coverage_geojson(dossier=None):
    """Génère la FeatureCollection GeoJSON des emprises d'orthophotos pour la carte de couverture."""
    qs = Orthophoto.objects.filter(emprise__isnull=False)
    if dossier:
        qs = qs.filter(dossier=dossier)
    features = []
    for o in qs:
        try:
            geom = json.loads(o.emprise.geojson)
            features.append({
                'type': 'Feature',
                'geometry': geom,
                'properties': {
                    'nom': o.nom,
                    'date': o.date_prise.strftime('%d/%m/%Y') if o.date_prise else '',
                    'resolution': o.resolution,
                    'tiles_url': o.tiles_url,
                }
            })
        except Exception:
            continue
    return json.dumps({'type': 'FeatureCollection', 'features': features})
