from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import NouvelleConstruction
from foncier.models import Espace


@receiver(pre_save, sender=NouvelleConstruction)
def construction_pre_save(sender, instance, **kwargs):
    """Mémorise l'ancien statut avant la sauvegarde."""
    if instance.pk:
        try:
            instance._ancien_statut = (
                NouvelleConstruction.objects.get(pk=instance.pk).statut
            )
        except NouvelleConstruction.DoesNotExist:
            instance._ancien_statut = None
    else:
        instance._ancien_statut = None


@receiver(post_save, sender=NouvelleConstruction)
def construction_post_save(sender, instance, created, **kwargs):
    """
    Recalcule la superficie disponible des espaces fonciers concernés
    à chaque changement de statut d'une construction.

    Règles :
    - L'espace reste LIBRE tant qu'il reste de la superficie constructible.
    - Le champ 'usage' est mis à jour avec le bilan : constructible / engagée / disponible.
    - Si la superficie disponible nette atteint 0, l'espace passe à OCCUPE.
    - Si une annulation libère de nouveau de la superficie, l'espace repasse à LIBRE.
    """
    ancien = getattr(instance, '_ancien_statut', None)
    nouveau = instance.statut

    if ancien == nouveau or not instance.zone_souhaitee:
        return

    # Espaces (libres ou occupés par constructions) qui intersectent la zone
    espaces = Espace.objects.filter(
        geometrie__intersects=instance.zone_souhaitee,
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE],
    )

    for espace in espaces:
        _recalculer_espace(espace)


def _recalculer_espace(espace):
    """
    Recalcule la superficie disponible nette d'un espace
    et met à jour son type et son usage en conséquence.
    """
    # Constructions approuvées / en cours / terminées dans cet espace
    # Le filtre zone_souhaitee__isnull=False évite les comportements inattendus
    # de PostGIS quand zone_souhaitee est NULL
    constructions = NouvelleConstruction.objects.filter(
        statut__in=NouvelleConstruction.STATUTS_ENGAGES,
        zone_souhaitee__isnull=False,
        zone_souhaitee__intersects=espace.geometrie,
    )
    sup_engagee     = sum(c.superficie_souhaitee or 0 for c in constructions)
    sup_brute       = espace.superficie or 0
    sup_constructible = sup_brute * (espace.taux_occupation / 100)
    sup_disponible  = max(0.0, sup_constructible - sup_engagee)

    if sup_engagee == 0:
        # Aucune construction engagée → espace entièrement libre
        if espace.type_espace == Espace.TYPE_OCCUPE:
            espace.type_espace = Espace.TYPE_LIBRE
            espace.save()

    elif sup_disponible <= 0:
        # Toute la superficie constructible est allouée → occupé
        if espace.type_espace != Espace.TYPE_OCCUPE:
            espace.type_espace = Espace.TYPE_OCCUPE
            espace.save()

    else:
        # Partiellement alloué → reste libre
        if espace.type_espace == Espace.TYPE_OCCUPE:
            espace.type_espace = Espace.TYPE_LIBRE
            espace.save()
