from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import NouvelleConstruction
from foncier.models import Espace

# Statuts qui réduisent la superficie affichée comme disponible (engagement formel)
_STATUTS_ENGAGES = NouvelleConstruction.STATUTS_ENGAGES

# Statuts qui occupent physiquement l'espace (travaux démarrés ou terminés)
_STATUTS_EFFECTIFS = [NouvelleConstruction.STATUT_EN_COURS, NouvelleConstruction.STATUT_TERMINE]


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
    Recalcule le type (LIBRE/OCCUPE) des espaces fonciers concernés
    à chaque changement de statut d'une construction.

    Deux niveaux :
    - Approuvée + En cours + Terminée → réduit la superficie affichée comme disponible.
    - En cours + Terminée uniquement  → peut marquer l'espace comme OCCUPÉ si la
      superficie constructible est entièrement consommée par des travaux réels.
    """
    ancien = getattr(instance, '_ancien_statut', None)
    nouveau = instance.statut

    if ancien == nouveau:
        return

    # Collecter tous les espaces concernés (sans doublons)
    espaces_pks = set()

    # 1. Via la FK directe (espace sélectionné depuis la liste)
    if instance.espace_souhaitee_id:
        espaces_pks.add(instance.espace_souhaitee_id)

    # 2. Via l'intersection géométrique (zone dessinée ou convex_hull de l'espace)
    if instance.zone_souhaitee:
        espaces_pks.update(
            Espace.objects.filter(
                geometrie__intersects=instance.zone_souhaitee,
                type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE],
            ).values_list('pk', flat=True)
        )

    for espace in Espace.objects.filter(pk__in=espaces_pks):
        _recalculer_espace(espace)


def _pks_constructions(espace, statuts):
    """
    Retourne l'ensemble des PKs des constructions dans les statuts donnés
    qui concernent cet espace (via FK directe OU intersection géométrique).
    Déduplique automatiquement via un set.
    """
    pks = set()

    # Via FK directe
    pks.update(
        NouvelleConstruction.objects.filter(
            statut__in=statuts,
            espace_souhaitee=espace,
        ).values_list('pk', flat=True)
    )

    # Via intersection géométrique
    if espace.geometrie:
        pks.update(
            NouvelleConstruction.objects.filter(
                statut__in=statuts,
                zone_souhaitee__isnull=False,
                zone_souhaitee__intersects=espace.geometrie,
            ).values_list('pk', flat=True)
        )

    return pks


def _recalculer_espace(espace):
    """
    Recalcule et met à jour le type de l'espace (LIBRE / OCCUPE).

    Règles :
    - Si la superficie constructible est entièrement consommée par des constructions
      physiquement en cours ou terminées → OCCUPE.
    - Dans tous les autres cas → LIBRE (annulations ou simples approbations libèrent l'espace).
    - Les espaces de type RESERVE ne sont jamais modifiés automatiquement.
    """
    if espace.type_espace == Espace.TYPE_RESERVE:
        return

    sup_brute = espace.superficie or 0
    sup_constructible = sup_brute * (espace.taux_occupation / 100)

    if sup_constructible <= 0:
        return

    # Superficies des constructions physiquement actives (en cours + terminées)
    pks_effectifs = _pks_constructions(espace, _STATUTS_EFFECTIFS)
    sup_effective = sum(
        c.superficie_souhaitee or 0
        for c in NouvelleConstruction.objects.filter(pk__in=pks_effectifs)
    ) if pks_effectifs else 0.0

    # Superficie nette restante (tolérance de 1 m² pour les arrondis flottants)
    sup_nette = max(0.0, sup_constructible - sup_effective)

    if sup_nette < 1.0:
        # Toute la superficie constructible est physiquement occupée (à 1 m² près)
        if espace.type_espace != Espace.TYPE_OCCUPE:
            espace.type_espace = Espace.TYPE_OCCUPE
            espace.save()
    else:
        # De l'espace est encore disponible (ou libéré après annulation)
        if espace.type_espace == Espace.TYPE_OCCUPE:
            espace.type_espace = Espace.TYPE_LIBRE
            espace.save()
