from django.db.models import Q
from territoire.models import Voirie, EspaceVert, PointInteret


def get_voiries_queryset(q: str = '', type_voirie: str = ''):
    """Retourne le réseau viaire filtré."""
    qs = Voirie.objects.all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q) | Q(type_voirie__icontains=q))
    if type_voirie:
        qs = qs.filter(type_voirie=type_voirie)
    return qs.order_by('nom')


def get_voirie_by_id(pk: int):
    """Résout une voirie par son ID."""
    return Voirie.objects.filter(pk=pk).first()


def get_espaces_verts_queryset(q: str = ''):
    """Retourne les espaces verts répertoriés."""
    qs = EspaceVert.objects.all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q) | Q(type_espace_vert__icontains=q))
    return qs.order_by('nom')


def get_espace_vert_by_id(pk: int):
    """Résout un espace vert par son ID."""
    return EspaceVert.objects.filter(pk=pk).first()
