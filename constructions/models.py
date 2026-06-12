from django.contrib.gis.db import models
from django.conf import settings
from foncier.models import Batiment, Espace


class NouvelleConstruction(models.Model):
    STATUT_ATTENTE = 'attente'
    STATUT_APPROUVE = 'approuvee'
    STATUT_REJETE = 'rejetee'
    STATUT_EN_COURS = 'en_cours'
    STATUT_TERMINE = 'terminee'

    STATUTS = [
        (STATUT_ATTENTE, 'En attente'),
        (STATUT_APPROUVE, 'Approuvée'),
        (STATUT_REJETE, 'Rejetée'),
        (STATUT_EN_COURS, 'En cours'),
        (STATUT_TERMINE, 'Terminée'),
    ]

    BADGE_COULEURS = {
        STATUT_ATTENTE: 'warning',
        STATUT_APPROUVE: 'success',
        STATUT_REJETE: 'danger',
        STATUT_EN_COURS: 'info',
        STATUT_TERMINE: 'secondary',
    }

    nom_projet = models.CharField(max_length=200, verbose_name='Nom du projet')
    type_construction = models.CharField(max_length=200, verbose_name='Type de construction')
    superficie_souhaitee = models.FloatField(verbose_name='Superficie souhaitée (m²)')
    zone_souhaitee = models.PolygonField(srid=4326, blank=True, null=True,
                                          verbose_name='Zone souhaitée')
    disponible = models.BooleanField(null=True, blank=True, verbose_name='Zone disponible')
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_ATTENTE)
    rapport_faisabilite = models.TextField(blank=True, verbose_name='Rapport de faisabilité')
    zones_alternatives = models.TextField(blank=True, verbose_name='Zones alternatives proposées')
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='Demandeur'
    )
    date_demande = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Nouvelle Construction'
        verbose_name_plural = 'Nouvelles Constructions'
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.nom_projet} ({self.get_statut_display()})"

    @property
    def badge_couleur(self):
        return self.BADGE_COULEURS.get(self.statut, 'secondary')

    def analyser_disponibilite(self):
        """Vérifie si la zone souhaitée peut accueillir la construction.
        Retourne (disponible, rapport, zones_alternatives_qs).
        """
        alternatives = Espace.objects.none()

        if not self.zone_souhaitee:
            return False, "Aucune zone dessinée sur la carte.", alternatives

        espaces_intersectant = Espace.objects.filter(
            type_espace=Espace.TYPE_LIBRE,
            geometrie__intersects=self.zone_souhaitee
        )

        if espaces_intersectant.exists():
            superficie_dispo = sum(e.superficie or 0 for e in espaces_intersectant)
            noms = ', '.join(e.nom for e in espaces_intersectant)

            if superficie_dispo >= self.superficie_souhaitee:
                self.disponible = True
                self.rapport_faisabilite = (
                    f"La zone sélectionnée est disponible. "
                    f"Espace(s) libre(s) : {noms}. "
                    f"Superficie libre : {superficie_dispo:.0f} m² "
                    f"pour un besoin de {self.superficie_souhaitee:.0f} m²."
                )
                self.zones_alternatives = ''
            else:
                self.disponible = False
                self.rapport_faisabilite = (
                    f"Superficie insuffisante dans la zone sélectionnée. "
                    f"Disponible : {superficie_dispo:.0f} m², "
                    f"requis : {self.superficie_souhaitee:.0f} m²."
                )
        else:
            self.disponible = False
            self.rapport_faisabilite = (
                "La zone sélectionnée ne contient aucun espace libre. "
                "Elle est déjà occupée ou réservée."
            )

        # Proposer des zones alternatives si non disponible
        if not self.disponible:
            alternatives = Espace.objects.filter(
                type_espace=Espace.TYPE_LIBRE,
                superficie__gte=self.superficie_souhaitee
            ).order_by('superficie')[:6]
            if alternatives.exists():
                noms_alt = ', '.join(
                    f"{e.nom} ({e.superficie:.0f} m²)" for e in alternatives
                )
                self.zones_alternatives = noms_alt

        self.save()
        return self.disponible, self.rapport_faisabilite, alternatives

    # Alias conservé pour compatibilité
    def analyser_faisabilite(self):
        disponible, rapport, _ = self.analyser_disponibilite()
        return disponible, rapport


class HistoriqueConstruction(models.Model):
    TYPE_CONSTRUCTION = 'construction'
    TYPE_RENOVATION = 'renovation'
    TYPE_EXTENSION = 'extension'
    TYPE_DEMOLITION = 'demolition'

    TYPES_TRAVAUX = [
        (TYPE_CONSTRUCTION, 'Construction'),
        (TYPE_RENOVATION, 'Rénovation'),
        (TYPE_EXTENSION, 'Extension'),
        (TYPE_DEMOLITION, 'Démolition'),
    ]

    batiment = models.ForeignKey(
        Batiment, on_delete=models.CASCADE,
        related_name='historiques', verbose_name='Bâtiment'
    )
    type_travaux = models.CharField(max_length=20, choices=TYPES_TRAVAUX,
                                     verbose_name='Type de travaux')
    date_debut = models.DateField(verbose_name='Date de début')
    date_fin = models.DateField(blank=True, null=True, verbose_name='Date de fin')
    description = models.TextField(verbose_name='Description')
    cout = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True,
                                verbose_name='Coût estimé (FCFA)')
    maitre_ouvrage = models.CharField(max_length=200, blank=True,
                                       verbose_name='Maître d\'ouvrage')
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historique de Construction'
        verbose_name_plural = 'Historique des Constructions'
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.batiment.nom} - {self.get_type_travaux_display()} ({self.date_debut.year})"
