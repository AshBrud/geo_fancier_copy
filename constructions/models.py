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

    # Statuts qui engagent réellement de la superficie (espace "pris")
    STATUTS_ENGAGES = ['approuvee', 'en_cours', 'terminee']

    # ------------------------------------------------------------------ #
    #  MÉTHODES INTERNES D'ANALYSE SPATIALE                               #
    # ------------------------------------------------------------------ #

    def _qs_engagees(self, zone):
        """Constructions approuvées/en cours/terminées qui intersectent une zone."""
        qs = NouvelleConstruction.objects.filter(
            statut__in=self.STATUTS_ENGAGES,
            zone_souhaitee__intersects=zone,
        )
        return qs.exclude(pk=self.pk) if self.pk else qs

    def _qs_en_attente(self, zone):
        """Constructions en attente concurrentes qui intersectent une zone."""
        qs = NouvelleConstruction.objects.filter(
            statut=self.STATUT_ATTENTE,
            zone_souhaitee__intersects=zone,
        )
        return qs.exclude(pk=self.pk) if self.pk else qs

    def _superficie_engagee(self, zone):
        return sum(c.superficie_souhaitee or 0 for c in self._qs_engagees(zone))

    def _superficie_en_attente(self, zone):
        qs = self._qs_en_attente(zone)
        return sum(c.superficie_souhaitee or 0 for c in qs), qs.count()

    # ------------------------------------------------------------------ #
    #  REJET AUTOMATIQUE DES CONCURRENTES APRÈS APPROBATION               #
    # ------------------------------------------------------------------ #

    def rejeter_concurrents(self):
        """
        Appelée après approbation d'une construction.
        Parcourt toutes les demandes EN ATTENTE qui intersectent la même zone
        et rejette automatiquement celles qui ne peuvent plus être construites
        faute de superficie nette suffisante.
        Retourne la liste des constructions auto-rejetées.
        """
        if not self.zone_souhaitee or self.statut not in self.STATUTS_ENGAGES:
            return []

        concurrentes = self._qs_en_attente(self.zone_souhaitee)
        auto_rejetees = []

        for concurrent in concurrentes:
            if not concurrent.zone_souhaitee:
                continue

            # Recalculer la superficie nette pour cette demande concurrente
            espaces_libres = Espace.objects.filter(
                type_espace=Espace.TYPE_LIBRE,
                geometrie__intersects=concurrent.zone_souhaitee,
            )
            sup_brute = sum(e.superficie or 0 for e in espaces_libres)
            sup_engagee = concurrent._superficie_engagee(concurrent.zone_souhaitee)
            sup_nette = max(0, sup_brute - sup_engagee)

            if sup_nette < (concurrent.superficie_souhaitee or 0):
                note = (
                    f"\n[Rejet automatique le {self.date_modification.strftime('%d/%m/%Y')}] "
                    f"La construction « {self.nom_projet} » vient d'être approuvée "
                    f"et occupe {self.superficie_souhaitee:.0f} m² dans cette zone. "
                    f"Superficie nette restante : {sup_nette:.0f} m², "
                    f"insuffisante pour ce projet ({concurrent.superficie_souhaitee:.0f} m² requis)."
                )
                concurrent.statut = self.STATUT_REJETE
                concurrent.rapport_faisabilite = (concurrent.rapport_faisabilite or '') + note
                concurrent.disponible = False
                concurrent.save()
                auto_rejetees.append(concurrent)

        return auto_rejetees

    # ------------------------------------------------------------------ #
    #  ANALYSE PRINCIPALE DE DISPONIBILITÉ                                #
    # ------------------------------------------------------------------ #

    def analyser_disponibilite(self):
        """
        Analyse intelligente et complète :
          1. Calcule la superficie brute des espaces libres dans la zone.
          2. Soustrait les constructions déjà approuvées/en cours/terminées.
          3. Avertit sur les demandes concurrentes en attente.
          4. Détermine si la construction est faisable (superficie nette).
          5. Propose des alternatives réellement disponibles si non faisable.
        Retourne (disponible, rapport, zones_alternatives_qs).
        """
        alternatives = Espace.objects.none()

        if not self.zone_souhaitee:
            self.disponible = False
            self.rapport_faisabilite = "Aucune zone dessinée sur la carte."
            self.save()
            return False, self.rapport_faisabilite, alternatives

        # ---- 1. Espaces libres dans la zone ----
        espaces = Espace.objects.filter(
            type_espace=Espace.TYPE_LIBRE,
            geometrie__intersects=self.zone_souhaitee,
        )

        if not espaces.exists():
            self.disponible = False
            self.rapport_faisabilite = (
                "La zone sélectionnée ne contient aucun espace libre. "
                "Elle est occupée ou réservée."
            )
            self.zones_alternatives = ''
            self._proposer_alternatives()
            self.save()
            return False, self.rapport_faisabilite, Espace.objects.none()

        sup_brute   = sum(e.superficie or 0 for e in espaces)
        noms_espaces = ', '.join(e.nom for e in espaces)

        # ---- 2. Superficie engagée (approuvées/en cours/terminées) ----
        qs_eng      = self._qs_engagees(self.zone_souhaitee)
        sup_engagee = sum(c.superficie_souhaitee or 0 for c in qs_eng)
        nb_engagees = qs_eng.count()

        # ---- 3. Demandes concurrentes en attente ----
        sup_attente, nb_attente = self._superficie_en_attente(self.zone_souhaitee)

        # ---- 4. Superficie nette réelle ----
        sup_nette   = max(0.0, sup_brute - sup_engagee)
        sup_requise = self.superficie_souhaitee or 0

        # ---- 5. Construction du rapport structuré ----
        lignes = ["=" * 48]

        if sup_nette >= sup_requise:
            self.disponible = True
            lignes.append("RÉSULTAT : Zone disponible — Faisable")
        else:
            self.disponible = False
            lignes.append("RÉSULTAT : Zone insuffisante — Non faisable")

        lignes += [
            "=" * 48,
            f"Espace(s) concerné(s) : {noms_espaces}",
            "-" * 48,
            f"Superficie brute              : {sup_brute:>12,.0f} m²  ({sup_brute/10000:.2f} ha)",
        ]

        if nb_engagees > 0:
            lignes.append(
                f"Déjà allouée ({nb_engagees} construction(s)) : -{sup_engagee:>11,.0f} m²  ({sup_engagee/10000:.2f} ha)"
            )

        lignes += [
            f"Superficie nette disponible   : {sup_nette:>12,.0f} m²  ({sup_nette/10000:.2f} ha)",
            f"Superficie requise            : {sup_requise:>12,.0f} m²  ({sup_requise/10000:.2f} ha)",
        ]

        if not self.disponible:
            manque = sup_requise - sup_nette
            lignes.append(f"Manque                        : {manque:>12,.0f} m²  ({manque/10000:.2f} ha)")

        if nb_attente > 0:
            lignes += [
                "-" * 48,
                f"ATTENTION : {nb_attente} autre(s) demande(s) en attente",
                f"totalisant {sup_attente:,.0f} m² dans cette zone.",
                "La priorité sera accordée selon l'ordre d'approbation.",
                "Si cette demande est approuvée, les concurrentes",
                "incompatibles seront automatiquement rejetées.",
            ]

        if nb_engagees > 0:
            lignes += ["-" * 48, "Constructions engagées dans cette zone :"]
            for c in qs_eng:
                lignes.append(f"  • {c.nom_projet} — {c.superficie_souhaitee:,.0f} m² ({c.get_statut_display()})")

        lignes.append("=" * 48)
        self.rapport_faisabilite = "\n".join(lignes)
        self.zones_alternatives  = ''

        # ---- 6. Zones alternatives si non disponible ----
        if not self.disponible:
            alternatives = self._proposer_alternatives()

        self.save()
        return self.disponible, self.rapport_faisabilite, alternatives

    def _proposer_alternatives(self):
        """Cherche des espaces libres avec assez de superficie nette."""
        candidates = Espace.objects.filter(
            type_espace=Espace.TYPE_LIBRE,
            superficie__gte=self.superficie_souhaitee,
        ).order_by('superficie')

        valides = []
        for esp in candidates:
            eng = self._superficie_engagee(esp.geometrie)
            nette = max(0, (esp.superficie or 0) - eng)
            if nette >= (self.superficie_souhaitee or 0):
                valides.append((esp, nette))
            if len(valides) >= 6:
                break

        if valides:
            self.zones_alternatives = ', '.join(
                f"{e.nom} ({nette:,.0f} m² nets disponibles)"
                for e, nette in valides
            )
            return Espace.objects.filter(pk__in=[e.pk for e, _ in valides])

        self.zones_alternatives = "Aucune zone alternative disponible avec superficie suffisante."
        return Espace.objects.none()

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
