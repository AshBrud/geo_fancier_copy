from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import NouvelleConstruction
from foncier.models import Espace

# Statuts qui engagent/réservent un espace
_STATUTS_ENGAGES = [
    NouvelleConstruction.STATUT_APPROUVE,
    NouvelleConstruction.STATUT_EN_COURS,
]


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
    Met à jour le type et l'usage des espaces fonciers concernés
    dès qu'un statut de construction change.
    """
    ancien = getattr(instance, '_ancien_statut', None)
    nouveau = instance.statut

    # Aucun changement de statut ou aucune zone définie → rien à faire
    if ancien == nouveau or not instance.zone_souhaitee:
        return

    espaces_qs = Espace.objects.filter(
        geometrie__intersects=instance.zone_souhaitee,
    )

    # ── Construction terminée → espace occupé ──────────────────────────
    if nouveau == NouvelleConstruction.STATUT_TERMINE:
        espaces_qs.filter(
            type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_RESERVE],
        ).update(
            type_espace=Espace.TYPE_OCCUPE,
            usage=f"Construction achevée : {instance.nom_projet}",
        )

    # ── Construction approuvée ou en cours → espace réservé ────────────
    elif nouveau in _STATUTS_ENGAGES:
        espaces_qs.filter(
            type_espace=Espace.TYPE_LIBRE,
        ).update(
            type_espace=Espace.TYPE_RESERVE,
            usage=f"Réservé pour : {instance.nom_projet}",
        )

    # ── Construction rejetée ou remise en attente → libérer l'espace ───
    elif nouveau in (NouvelleConstruction.STATUT_REJETE, NouvelleConstruction.STATUT_ATTENTE):
        if ancien not in _STATUTS_ENGAGES:
            return  # L'espace n'avait pas été réservé par ce changement

        for espace in espaces_qs.filter(type_espace=Espace.TYPE_RESERVE):
            # Ne libérer que si aucune autre construction engagée intersecte cet espace
            autres_engagees = NouvelleConstruction.objects.filter(
                statut__in=NouvelleConstruction.STATUTS_ENGAGES,
                zone_souhaitee__intersects=espace.geometrie,
            ).exclude(pk=instance.pk)

            if not autres_engagees.exists():
                espace.type_espace = Espace.TYPE_LIBRE
                espace.usage = ''
                espace.save()
