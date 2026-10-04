from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import NouvelleConstruction
from dossiers.models import ZoneSecteur

# Statuts qui réduisent la superficie affichée comme disponible (engagement formel)
_STATUTS_ENGAGES = NouvelleConstruction.STATUTS_ENGAGES

# Statuts qui occupent physiquement l'espace (en cours ou approuvés)
_STATUTS_EFFECTIFS = [NouvelleConstruction.STATUT_EN_COURS, NouvelleConstruction.STATUT_APPROUVE]


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
    Recalcule l'état des zones territoriales concernées à chaque changement de statut.
    """
    ancien = getattr(instance, '_ancien_statut', None)
    nouveau = instance.statut

    if ancien == nouveau:
        return

    # Collecter toutes les zones concernées (sans doublons)
    zones_pks = set()

    # 1. Via la FK directe
    if instance.zone_secteur_id:
        zones_pks.add(instance.zone_secteur_id)

    # 2. Via l'intersection géométrique
    if instance.zone_souhaitee:
        zones_pks.update(
            ZoneSecteur.objects.filter(
                geometrie__intersects=instance.zone_souhaitee,
                type_zone__in=[ZoneSecteur.TYPE_ESPACE_LIBRE, ZoneSecteur.TYPE_SECTEUR_CAMPUS, ZoneSecteur.TYPE_ZONE_ACTIVITE],
            ).values_list('pk', flat=True)
        )

    # Création automatique du suivi dès qu'une construction est approuvée
    if (nouveau == NouvelleConstruction.STATUT_APPROUVE
            and ancien != NouvelleConstruction.STATUT_APPROUVE):
        from territoire.models.models_suivi_travaux import SuiviTravaux
        SuiviTravaux.objects.get_or_create(
            construction=instance,
            defaults={'maitre_ouvrage': instance.demandeur},
        )


def _pks_constructions(zone, statuts):
    """
    Retourne l'ensemble des PKs des constructions dans les statuts donnés
    qui concernent cette zone (via FK directe OU intersection géométrique).
    """
    pks = set()

    # Via FK directe
    pks.update(
        NouvelleConstruction.objects.filter(
            statut__in=statuts,
            zone_secteur=zone,
        ).values_list('pk', flat=True)
    )

    # Via intersection géométrique
    if zone.geometrie:
        pks.update(
            NouvelleConstruction.objects.filter(
                statut__in=statuts,
                zone_souhaitee__isnull=False,
                zone_souhaitee__intersects=zone.geometrie,
            ).values_list('pk', flat=True)
        )

    return pks
