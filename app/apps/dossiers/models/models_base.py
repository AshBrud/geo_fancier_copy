from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Socle abstrait d'audit et de traçabilité temporelle.
    Hérité par l'ensemble des entités du système GéoFoncier V2
    pour garantir un horodatage immuable et automatique.
    """
    date_creation = models.DateTimeField(
        default=timezone.now,
        blank=True,
        verbose_name="Date de création",
        help_text="Enregistré automatiquement lors de la création de la fiche."
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification",
        help_text="Mis à jour automatiquement lors de toute modification."
    )

    class Meta:
        abstract = True
        ordering = ['-date_creation']

    @property
    def formatted_date_creation(self) -> str:
        """Retourne la date de création au format lisible JJ/MM/AAAA HH:MM dans le fuseau actif."""
        if not self.date_creation:
            return ""
        dt = timezone.localtime(self.date_creation) if timezone.is_aware(self.date_creation) else self.date_creation
        return dt.strftime("%d/%m/%Y %H:%M")

    @property
    def formatted_date_modification(self) -> str:
        """Retourne la date de modification au format lisible JJ/MM/AAAA HH:MM dans le fuseau actif."""
        if not self.date_modification:
            return ""
        dt = timezone.localtime(self.date_modification) if timezone.is_aware(self.date_modification) else self.date_modification
        return dt.strftime("%d/%m/%Y %H:%M")
