from django.db.models import Q
from territoire.models import Terrain


def get_terrains_queryset(q: str = ''):
    """Retourne les parcelles et terrains répertoriés."""
    qs = Terrain.objects.all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q) | Q(type_terrain__icontains=q))
    return qs.order_by('nom')


def get_terrain_by_id(pk: int):
    """Résout un terrain par son ID."""
    return Terrain.objects.filter(pk=pk).first()
