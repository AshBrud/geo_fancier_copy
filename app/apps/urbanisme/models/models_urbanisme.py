
from django.conf import settings
from django.contrib.gis.db import models

from dossiers.models.models_base import TimeStampedModel


class NouvelleConstruction(TimeStampedModel):
    """
    Modèle de planification d'urbanisme et de projet d'implantation spatiale.
    Rattaché à un Dossier workspace et optionnellement à une ZoneSecteur.
    """
    STATUT_EN_COURS = 'en_cours'
    STATUT_APPROUVE = 'approuvee'
    STATUT_REJETE = 'rejetee'

    STATUTS = [
        (STATUT_EN_COURS, 'En cours d\'instruction'),
        (STATUT_APPROUVE, 'Approuvée / Autorisée'),
        (STATUT_REJETE, 'Rejetée'),
    ]

    BADGE_COULEURS = {
        STATUT_EN_COURS: 'info',
        STATUT_APPROUVE: 'success',
        STATUT_REJETE: 'danger',
    }

    nom_projet = models.CharField(max_length=200, verbose_name='Nom du projet')
    type_construction = models.CharField(max_length=200, verbose_name='Type de construction')
    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Dossier territorial',
        related_name='projets_construction',
    )
    zone_secteur = models.ForeignKey(
        'dossiers.ZoneSecteur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Zone ou secteur ciblé',
        related_name='projets_construction',
    )
    superficie_souhaitee = models.FloatField(verbose_name='Superficie souhaitée (m²)')
    zone_souhaitee = models.PolygonField(
        srid=4326, blank=True, null=True,
        verbose_name='Zone souhaitée'
    )
    disponible = models.BooleanField(null=True, blank=True, verbose_name='Zone disponible')
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_EN_COURS, verbose_name='Statut')
    rapport_faisabilite = models.TextField(blank=True, verbose_name='Rapport de faisabilité')
    zones_alternatives = models.TextField(blank=True, verbose_name='Zones alternatives proposées')
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='Demandeur'
    )
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name='Date de demande')

    class Meta:
        verbose_name = 'Nouvelle Construction'
        verbose_name_plural = 'Nouvelles Constructions'
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.nom_projet} ({self.get_statut_display()})"

    @property
    def badge_couleur(self):
        return self.BADGE_COULEURS.get(self.statut, 'secondary')

    STATUTS_ENGAGES = ['approuvee', 'en_cours']
    TAUX_OCCUPATION_MAX = 0.60

    # Délégation des méthodes analytiques à la couche services (imports locaux pour éviter les imports circulaires)
    def analyser_disponibilite(self):
        from urbanisme.services.services_faisabilite import analyser_disponibilite_projet
        return analyser_disponibilite_projet(self)

    def trouver_alternatives(self):
        from urbanisme.services.services_faisabilite import trouver_alternatives_projet
        return trouver_alternatives_projet(self)

    def analyser_faisabilite(self):
        disponible, rapport, _, _stats = self.analyser_disponibilite()
        return disponible, rapport

    @classmethod
    def superficie_allouee_espace(cls, espace, exclude_pk=None):
        from urbanisme.services.services_faisabilite import calculer_superficie_allouee_espace
        return calculer_superficie_allouee_espace(espace, exclude_pk=exclude_pk)

    def rejeter_concurrents(self):
        from urbanisme.services.services_faisabilite import rejeter_projets_concurrents
        return rejeter_projets_concurrents(self)

    @classmethod
    def bilan_espace(cls, espace, statuts=None, exclude_pk=None):
        from urbanisme.selectors.selectors_urbanisme import get_bilan_espace
        return get_bilan_espace(espace, statuts=statuts, exclude_pk=exclude_pk)


class HistoriqueConstruction(TimeStampedModel):
    """
    Historique des chantiers et interventions sur le bâti.
    """
    TYPE_CONSTRUCTION = 'construction'
    TYPE_RENOVATION = 'renovation'
    TYPE_EXTENSION = 'extension'
    TYPE_DEMOLITION = 'demolition'

    TYPES_TRAVAUX = [
        (TYPE_CONSTRUCTION, 'Construction neuve'),
        (TYPE_RENOVATION, 'Rénovation / Réhabilitation'),
        (TYPE_EXTENSION, 'Extension / Agrandissement'),
        (TYPE_DEMOLITION, 'Démolition / Déconstruction'),
    ]

    unite_batie = models.ForeignKey(
        'dossiers.UniteBatie', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='historiques_travaux', verbose_name='Unité bâtie'
    )
    type_travaux = models.CharField(
        max_length=20, choices=TYPES_TRAVAUX,
        verbose_name='Nature des travaux'
    )
    date_debut = models.DateField(verbose_name='Date de démarrage')
    date_fin = models.DateField(blank=True, null=True, verbose_name='Date d\'achèvement')
    description = models.TextField(verbose_name='Descriptif des travaux')
    cout = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True,
        verbose_name='Coût engagé (FCFA)'
    )
    maitre_ouvrage = models.CharField(
        max_length=200, blank=True,
        verbose_name='Maître d\'ouvrage / Prestataire'
    )

    class Meta:
        verbose_name = 'Historique de Construction'
        verbose_name_plural = 'Historiques de Constructions'
        ordering = ['-date_debut']

    def __str__(self):
        cible = self.unite_batie.nom if self.unite_batie else "Bâti"
        return f"{cible} - {self.get_type_travaux_display()} ({self.date_debut.year})"
