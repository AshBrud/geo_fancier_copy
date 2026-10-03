from django.db.models import Q, Sum
from territoire.models import Batiment, FonctionBatiment


def get_batiments_queryset(q: str = '', fonction_id: int = None):
    """Retourne le queryset ordonné des bâtiments avec jointure fonction."""
    qs = Batiment.objects.select_related('fonction').all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    if fonction_id:
        qs = qs.filter(fonction_id=fonction_id)
    return qs.order_by('nom')


def get_batiment_by_id(pk: int):
    """Résout un bâtiment par sa clé primaire."""
    return Batiment.objects.filter(pk=pk).select_related('fonction').first()


def get_batiments_stats():
    """Calcule les indicateurs globaux du parc bâti."""
    total = Batiment.objects.count()
    actifs = Batiment.objects.filter(est_actif=True).count()
    superficie_totale = Batiment.objects.aggregate(s=Sum('superficie'))['s'] or 0.0
    return {
        'total': total,
        'actifs': actifs,
        'superficie_totale': superficie_totale,
        'superficie_ha': round(superficie_totale / 10000, 2) if superficie_totale else 0.0,
    }
