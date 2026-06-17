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

    # Statuts qui engagent réellement de la superficie
    STATUTS_ENGAGES = ['approuvee', 'en_cours', 'terminee']

    def _superficie_deja_allouee(self, zone):
        """Retourne la superficie (m²) déjà allouée à des constructions
        approuvées/en cours/terminées qui intersectent la zone donnée."""
        qs = NouvelleConstruction.objects.filter(
            statut__in=self.STATUTS_ENGAGES,
            zone_souhaitee__intersects=zone,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return sum(c.superficie_souhaitee or 0 for c in qs)

    def analyser_disponibilite(self):
        """Vérifie si la zone souhaitée peut accueillir la construction
        en tenant compte des constructions déjà approuvées.
        Retourne (disponible, rapport, zones_alternatives_qs).
        """
        alternatives = Espace.objects.none()

        if not self.zone_souhaitee:
            return False, "Aucune zone dessinée sur la carte.", alternatives

        # Espaces libres qui intersectent la zone demandée
        espaces_intersectant = Espace.objects.filter(
            type_espace=Espace.TYPE_LIBRE,
            geometrie__intersects=self.zone_souhaitee
        )

        if espaces_intersectant.exists():
            superficie_brute = sum(e.superficie or 0 for e in espaces_intersectant)
            noms = ', '.join(e.nom for e in espaces_intersectant)

            # Soustraire la superficie déjà allouée aux constructions engagées
            deja_allouee = self._superficie_deja_allouee(self.zone_souhaitee)
            superficie_nette = max(0, superficie_brute - deja_allouee)

            if superficie_nette >= self.superficie_souhaitee:
                self.disponible = True
                if deja_allouee > 0:
                    self.rapport_faisabilite = (
                        f"Zone disponible malgré des constructions existantes. "
                        f"Espace(s) : {noms}. "
                        f"Superficie brute : {superficie_brute:.0f} m² — "
                        f"Déjà allouée : {deja_allouee:.0f} m² — "
                        f"Disponible nette : {superficie_nette:.0f} m² "
                        f"pour un besoin de {self.superficie_souhaitee:.0f} m²."
                    )
                else:
                    self.rapport_faisabilite = (
                        f"La zone sélectionnée est disponible. "
                        f"Espace(s) libre(s) : {noms}. "
                        f"Superficie disponible : {superficie_nette:.0f} m² "
                        f"pour un besoin de {self.superficie_souhaitee:.0f} m²."
                    )
                self.zones_alternatives = ''
            else:
                self.disponible = False
                detail = (
                    f"Superficie brute de la zone : {superficie_brute:.0f} m²"
                )
                if deja_allouee > 0:
                    detail += (
                        f", dont {deja_allouee:.0f} m² déjà alloués à "
                        f"{NouvelleConstruction.objects.filter(statut__in=self.STATUTS_ENGAGES, zone_souhaitee__intersects=self.zone_souhaitee).count()} "
                        f"construction(s) approuvée(s)"
                    )
                self.rapport_faisabilite = (
                    f"Superficie insuffisante dans la zone sélectionnée. "
                    f"{detail}. "
                    f"Superficie nette disponible : {superficie_nette:.0f} m², "
                    f"superficie requise : {self.superficie_souhaitee:.0f} m²."
                )
        else:
            self.disponible = False
            self.rapport_faisabilite = (
                "La zone sélectionnée ne contient aucun espace libre. "
                "Elle est déjà occupée ou réservée."
            )

        # Proposer des zones alternatives si non disponible
        if not self.disponible:
            # Chercher des espaces libres avec suffisamment de superficie nette
            candidates = Espace.objects.filter(
                type_espace=Espace.TYPE_LIBRE,
                superficie__gte=self.superficie_souhaitee
            ).order_by('superficie')

            alternatives_list = []
            for esp in candidates:
                deja = self._superficie_deja_allouee(esp.geometrie)
                superficie_nette_esp = max(0, (esp.superficie or 0) - deja)
                if superficie_nette_esp >= self.superficie_souhaitee:
                    alternatives_list.append(esp)
                if len(alternatives_list) >= 6:
                    break

            if alternatives_list:
                noms_alt = ', '.join(
                    f"{e.nom} ({(e.superficie or 0) - self._superficie_deja_allouee(e.geometrie):.0f} m² nets)"
                    for e in alternatives_list
                )
                self.zones_alternatives = noms_alt
                # Retourner un queryset filtré sur les ids trouvés
                ids = [e.pk for e in alternatives_list]
                alternatives = Espace.objects.filter(pk__in=ids)
            else:
                self.zones_alternatives = "Aucune zone alternative avec superficie suffisante disponible."
                alternatives = Espace.objects.none()

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
