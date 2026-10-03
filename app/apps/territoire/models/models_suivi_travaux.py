from django.db import models
from django.conf import settings


class SuiviTravaux(models.Model):
    STATUT_NON_DEMARRE = 'non_demarre'
    STATUT_EN_COURS = 'en_cours'
    STATUT_TERMINE = 'termine'

    STATUTS = [
        (STATUT_NON_DEMARRE, 'Non démarré'),
        (STATUT_EN_COURS, 'En cours'),
        (STATUT_TERMINE, 'Terminé'),
    ]

    BADGE_COULEURS = {
        STATUT_NON_DEMARRE: 'secondary',
        STATUT_EN_COURS: 'info',
        STATUT_TERMINE: 'success',
    }

    construction = models.OneToOneField(
        'urbanisme.NouvelleConstruction',
        on_delete=models.CASCADE,
        related_name='suivi',
        verbose_name='Demande de construction',
    )
    maitre_ouvrage = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Maître d'ouvrage",
        related_name='travaux_diriges',
    )
    statut = models.CharField(
        max_length=20, choices=STATUTS, default=STATUT_NON_DEMARRE,
        verbose_name='Statut des travaux',
    )
    date_debut = models.DateField(null=True, blank=True, verbose_name='Date de début')
    date_fin_prevue = models.DateField(null=True, blank=True, verbose_name='Date de fin prévue')
    observations = models.TextField(blank=True, verbose_name='Observations')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Suivi des travaux'
        verbose_name_plural = 'Suivis des travaux'
        ordering = ['-date_creation']

    def __str__(self):
        return f"Suivi — {self.construction.nom_projet}"

    @property
    def badge_couleur(self):
        return self.BADGE_COULEURS.get(self.statut, 'secondary')
