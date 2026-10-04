from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from .models_base import TimeStampedModel


def get_default_srid_for_geom(geom) -> int:
    """
    Détermine la projection métrique UTM appropriée selon la longitude centroïde.
    Sénégal Ouest (Dakar, Bambey, Thiès, Diourbel) : UTM 28N (EPSG:32628)
    Sénégal Est (Matam, Tambacounda, Kédougou) : UTM 29N (EPSG:32629)
    """
    if geom and hasattr(geom, 'centroid'):
        lon = geom.centroid.x
        return 32628 if lon < -12.0 else 32629
    return 32628


# =============================================================================
# 1. SUBDIVISIONS TERRITORIALES (UNIFICATION ESPACE & VILLAGE)
# =============================================================================

class ZoneSecteur(TimeStampedModel):
    """
    Subdivision spatiale territoriale unifiée (Zone, Secteur, Village, Quartier).
    Remplace et réconcilie 'foncier.Espace' (Campus) et 'commune.Village' (Commune).
    """
    TYPE_VILLAGE = 'village'
    TYPE_QUARTIER = 'quartier'
    TYPE_SECTEUR_CAMPUS = 'secteur_campus'
    TYPE_ESPACE_LIBRE = 'espace_libre'
    TYPE_ESPACE_RESERVE = 'espace_reserve'
    TYPE_ZONE_AGRICOLE = 'zone_agricole'
    TYPE_ZONE_ACTIVITE = 'zone_activite'
    TYPE_AUTRE = 'autre'

    TYPES_ZONE = [
        (TYPE_VILLAGE, 'Village'),
        (TYPE_QUARTIER, 'Quartier urbain'),
        (TYPE_SECTEUR_CAMPUS, 'Secteur d\'aménagement universitaire'),
        (TYPE_ESPACE_LIBRE, 'Espace libre / Réserve foncière'),
        (TYPE_ESPACE_RESERVE, 'Espace réservé'),
        (TYPE_ZONE_AGRICOLE, 'Zone agricole / pastorale'),
        (TYPE_ZONE_ACTIVITE, 'Zone d\'activités & équipements'),
        (TYPE_AUTRE, 'Autre zonage'),
    ]

    STATUT_ACTIF = 'actif'
    STATUT_EN_ETUDE = 'en_etude'
    STATUT_ARCHIVE = 'archive'

    STATUTS = [
        (STATUT_ACTIF, 'Actif'),
        (STATUT_EN_ETUDE, 'En cours d\'aménagement / étude'),
        (STATUT_ARCHIVE, 'Archivé / Obsolète'),
    ]

    COULEURS_ZONE = {
        TYPE_VILLAGE: '#059669',
        TYPE_QUARTIER: '#2563EB',
        TYPE_SECTEUR_CAMPUS: '#7C3AED',
        TYPE_ESPACE_LIBRE: '#16A34A',
        TYPE_ESPACE_RESERVE: '#D97706',
        TYPE_ZONE_AGRICOLE: '#84CC16',
        TYPE_ZONE_ACTIVITE: '#EA580C',
        TYPE_AUTRE: '#64748B',
    }

    TOLERANCE_DEBORDEMENT = 0.02

    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        related_name='zones_secteurs',
        verbose_name="Dossier territorial",
        help_text="Workspace territorial de rattachement."
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Identifiant de zone",
        help_text="Code technique unique (ex: V-001, SEC-01). Généré automatiquement si vide."
    )
    nom = models.CharField(
        max_length=200,
        verbose_name="Nom de la zone ou village",
        help_text="Désignation toponymique usuelle."
    )
    type_zone = models.CharField(
        max_length=50,
        choices=TYPES_ZONE,
        default=TYPE_VILLAGE,
        verbose_name="Nature de la subdivision"
    )
    statut = models.CharField(
        max_length=30,
        choices=STATUTS,
        default=STATUT_ACTIF,
        verbose_name="Statut opérationnel"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description & Contexte"
    )
    geometrie = models.MultiPolygonField(
        srid=4326,
        verbose_name="Emprise spatiale (WGS 84)"
    )
    superficie_m2 = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Superficie (m²)"
    )
    superficie_ha = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Superficie (ha)"
    )
    population_estimee = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Population estimée"
    )
    responsable_nom = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Responsable / Chef de village"
    )
    responsable_telephone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Téléphone de contact"
    )
    metadata_specifique = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Métadonnées spécifiques"
    )

    class Meta:
        verbose_name = "Zone & Secteur territorial"
        verbose_name_plural = "Zones & Secteurs territoriaux"
        ordering = ['dossier', 'nom']
        unique_together = ('dossier', 'code')

    def __str__(self):
        return f"{self.nom} [{self.code}] — {self.dossier.nom}"

    @property
    def superficie_km2(self) -> float:
        return round(self.superficie_m2 / 1_000_000, 2) if self.superficie_m2 else 0.0

    @property
    def couleur(self) -> str:
        return self.COULEURS_ZONE.get(self.type_zone, '#2563EB')

    @property
    def nb_unites_baties(self) -> int:
        if 'nb_unites_baties' in self.__dict__:
            return self.__dict__['nb_unites_baties']
        return self.unites_baties.count()

    @nb_unites_baties.setter
    def nb_unites_baties(self, val):
        self.__dict__['nb_unites_baties'] = val

    @property
    def surface_batie_m2(self) -> float:
        if 'surface_batie_m2' in self.__dict__:
            return self.__dict__['surface_batie_m2'] or 0.0
        from django.db.models import Sum
        return float(self.unites_baties.aggregate(s=Sum('superficie_m2'))['s'] or 0.0)

    @surface_batie_m2.setter
    def surface_batie_m2(self, val):
        self.__dict__['surface_batie_m2'] = val

    def clean(self):
        if not self.geometrie or not self.dossier_id:
            return
        if self.dossier.geometrie:
            srid = self.dossier.srid_projection or get_default_srid_for_geom(self.geometrie)
            g = self.geometrie.transform(srid, clone=True)
            d = self.dossier.geometrie.transform(srid, clone=True)
            if g.area and d.area:
                debordement = g.difference(d).area
                if debordement / g.area > self.TOLERANCE_DEBORDEMENT:
                    raise ValidationError(
                        f"Le polygone de la zone « {self.nom} » déborde significativement "
                        f"(> {self.TOLERANCE_DEBORDEMENT * 100:.0f}%) des limites officielles du dossier « {self.dossier.nom} »."
                    )

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "SEC" if self.type_zone == self.TYPE_SECTEUR_CAMPUS else "Z"
            count = ZoneSecteur.objects.filter(dossier=self.dossier).count() + 1
            code_propose = f"{prefix}-{count:03d}"
            while ZoneSecteur.objects.filter(dossier=self.dossier, code=code_propose).exists():
                count += 1
                code_propose = f"{prefix}-{count:03d}"
            self.code = code_propose

        if self.geometrie:
            target_srid = self.dossier.srid_projection if self.dossier else get_default_srid_for_geom(self.geometrie)
            geom_utm = self.geometrie.transform(target_srid, clone=True)
            self.superficie_m2 = round(geom_utm.area, 2)
            self.superficie_ha = round(self.superficie_m2 / 10000, 4)

        super().save(*args, **kwargs)


# =============================================================================
# 2. RECENSEMENT BÂTI (UNIFICATION BATIMENT & MAISON)
# =============================================================================

class UniteBatie(TimeStampedModel):
    """
    Unité bâtie recensée (Bâtiment institutionnel, Maison, Concession, Infrastructure).
    Remplace et réconcilie 'foncier.Batiment' et 'commune.Maison'.
    """
    TYPE_HABITATION = 'habitation'
    TYPE_ADMINISTRATIF = 'administratif'
    TYPE_PEDAGOGIQUE = 'pedagogique'
    TYPE_SANITAIRE = 'sanitaire'
    TYPE_COMMERCIAL = 'commercial'
    TYPE_CULTE = 'culte'
    TYPE_SPORTIF = 'sportif'
    TYPE_STOCKAGE = 'stockage'
    TYPE_AUTRE = 'autre'

    TYPES_BATI = [
        (TYPE_HABITATION, 'Habitation / Concession'),
        (TYPE_ADMINISTRATIF, 'Bâtiment administratif'),
        (TYPE_PEDAGOGIQUE, 'Enseignement / Pédagogique'),
        (TYPE_SANITAIRE, 'Santé / Dispensaire'),
        (TYPE_COMMERCIAL, 'Commerce / Marché'),
        (TYPE_CULTE, 'Lieu de culte'),
        (TYPE_SPORTIF, 'Infrastructure sportive'),
        (TYPE_STOCKAGE, 'Entrepôt / Stockage'),
        (TYPE_AUTRE, 'Autre édifice'),
    ]

    OCCUPATION_HABITEE = 'habitee'
    OCCUPATION_VACANT = 'non_habitee'
    OCCUPATION_EN_CONSTRUCTION = 'en_construction'
    OCCUPATION_RUINE = 'ruine'

    STATUTS_OCCUPATION = [
        (OCCUPATION_HABITEE, 'Occupé / Habité'),
        (OCCUPATION_VACANT, 'Vacant / Non habité'),
        (OCCUPATION_EN_CONSTRUCTION, 'En cours de construction'),
        (OCCUPATION_RUINE, 'Dégradé / En ruine'),
    ]

    COULEURS_STATUT = {
        OCCUPATION_HABITEE: '#16A34A',
        OCCUPATION_VACANT: '#94A3B8',
        OCCUPATION_EN_CONSTRUCTION: '#F59E0B',
        OCCUPATION_RUINE: '#DC2626',
    }

    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        related_name='unites_baties',
        verbose_name="Dossier territorial"
    )
    zone_secteur = models.ForeignKey(
        ZoneSecteur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unites_baties',
        verbose_name="Zone ou village de rattachement"
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Identifiant unique du bâti",
        help_text="Ex: BAT-001, M-0042. Généré automatiquement si vide."
    )
    nom = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Désignation / Nom usuel",
        help_text="Ex: Amphithéâtre Diop, Concession Ndiaye."
    )
    type_bati = models.CharField(
        max_length=40,
        choices=TYPES_BATI,
        default=TYPE_HABITATION,
        verbose_name="Usage principal du bâti"
    )
    statut_occupation = models.CharField(
        max_length=30,
        choices=STATUTS_OCCUPATION,
        default=OCCUPATION_HABITEE,
        verbose_name="Statut d'occupation"
    )
    etages = models.PositiveIntegerField(
        default=1,
        verbose_name="Nombre de niveaux (R+N)"
    )
    annee_construction = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Année d'édification"
    )
    geometrie = models.MultiPolygonField(
        srid=4326,
        verbose_name="Emprise au sol (WGS 84)"
    )
    superficie_m2 = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Superficie au sol (m²)"
    )
    superficie_ha = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Superficie au sol (ha)"
    )
    photo = models.ImageField(
        upload_to='unites_baties/',
        blank=True,
        null=True,
        verbose_name="Cliché terrain / drone"
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name="Bâtiment existant et actif"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Notes / Observations techniques"
    )
    metadata_specifique = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Attributs spécifiques du bâti",
        help_text="Structure murs, toiture, équipement solaire, raccordement eau, etc."
    )

    class Meta:
        verbose_name = "Unité bâtie"
        verbose_name_plural = "Unités bâties"
        ordering = ['dossier', 'code']
        unique_together = ('dossier', 'code')

    def __str__(self):
        designation = self.nom or self.get_type_bati_display()
        return f"{self.code} — {designation} ({self.dossier.nom})"

    @property
    def couleur_statut(self) -> str:
        return self.COULEURS_STATUT.get(self.statut_occupation, '#94A3B8')

    @property
    def emprise_sol_m2(self):
        """Alias pour superficie_m2."""
        if 'emprise_sol_m2' in self.__dict__:
            return self.__dict__['emprise_sol_m2']
        return self.superficie_m2

    @emprise_sol_m2.setter
    def emprise_sol_m2(self, val):
        self.__dict__['emprise_sol_m2'] = val
        self.superficie_m2 = val

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "BAT" if self.type_bati != self.TYPE_HABITATION else "MAIS"
            count = UniteBatie.objects.filter(dossier=self.dossier).count() + 1
            code_propose = f"{prefix}-{count:04d}"
            while UniteBatie.objects.filter(dossier=self.dossier, code=code_propose).exists():
                count += 1
                code_propose = f"{prefix}-{count:04d}"
            self.code = code_propose

        if self.geometrie:
            target_srid = self.dossier.srid_projection if self.dossier else get_default_srid_for_geom(self.geometrie)
            geom_utm = self.geometrie.transform(target_srid, clone=True)
            self.superficie_m2 = round(geom_utm.area, 2)
            self.superficie_ha = round(self.superficie_m2 / 10000, 4)

        super().save(*args, **kwargs)


# =============================================================================
# 3. LINÉAIRES ET VOIRIES (UNIFICATION VOIRIE & PISTE)
# =============================================================================

class ReseauLineaire(TimeStampedModel):
    """
    Réseau de communication linéaire unifié (Route goudronnée, Latérite, Piste, Allée, etc.).
    Remplace et réconcilie 'foncier.Voirie' et 'commune.Piste'.
    """
    TYPE_ROUTE_BITUMEE = 'route_bitumee'
    TYPE_LATERITE = 'laterite'
    TYPE_PISTE = 'piste'
    TYPE_ALLEE_PIETONNE = 'allee_pietonne'
    TYPE_PARKING = 'parking'
    TYPE_CANALISATION = 'canalisation'
    TYPE_AUTRE = 'autre'

    TYPES_VOIE = [
        (TYPE_ROUTE_BITUMEE, 'Route bitumée'),
        (TYPE_LATERITE, 'Route en latérite'),
        (TYPE_PISTE, 'Piste en terre'),
        (TYPE_ALLEE_PIETONNE, 'Allée piétonne'),
        (TYPE_PARKING, 'Aire de stationnement / Parking'),
        (TYPE_CANALISATION, 'Réseau d\'assainissement / Canalisation'),
        (TYPE_AUTRE, 'Autre tracé linéaire'),
    ]

    COULEURS_VOIE = {
        TYPE_ROUTE_BITUMEE: '#1F2937',
        TYPE_LATERITE: '#B45309',
        TYPE_PISTE: '#D97706',
        TYPE_ALLEE_PIETONNE: '#059669',
        TYPE_PARKING: '#4B5563',
        TYPE_CANALISATION: '#0284C7',
        TYPE_AUTRE: '#6B7280',
    }

    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        related_name='reseaux_lineaires',
        verbose_name="Dossier territorial"
    )
    nom = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom / Tronçon",
        help_text="Ex: Axe Principal Nord-Sud, Tronçon Ngogom-Bambey."
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Identifiant du tronçon"
    )
    type_voie = models.CharField(
        max_length=40,
        choices=TYPES_VOIE,
        default=TYPE_PISTE,
        verbose_name="Nature de l'infrastructure"
    )
    geometrie = models.MultiLineStringField(
        srid=4326,
        verbose_name="Tracé cartographique (LineString WGS 84)"
    )
    longueur_metres = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Longueur métrique (m)",
        help_text="Calculée automatiquement en projection UTM."
    )
    largeur_estimee_m = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Largeur approximative de la voie (m)"
    )
    etat_chaussee = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="État de praticabilité",
        help_text="Bon, moyen, dégradé, impraticable en hivernage."
    )
    description = models.TextField(
        blank=True,
        verbose_name="Observations"
    )

    class Meta:
        verbose_name = "Réseau linéaire & voirie"
        verbose_name_plural = "Réseaux linéaires & voiries"
        ordering = ['dossier', 'type_voie', 'nom']

    def __str__(self):
        libelle = self.nom or f"{self.get_type_voie_display()}"
        return f"{libelle} ({self.dossier.nom})"

    @property
    def couleur(self) -> str:
        return self.COULEURS_VOIE.get(self.type_voie, '#D97706')

    @property
    def longueur_km(self) -> float:
        if 'longueur_km' in self.__dict__:
            return self.__dict__['longueur_km']
        return round(self.longueur_metres / 1000, 2) if self.longueur_metres else 0.0

    @longueur_km.setter
    def longueur_km(self, val):
        self.__dict__['longueur_km'] = val

    def save(self, *args, **kwargs):
        if not self.code:
            count = ReseauLineaire.objects.filter(dossier=self.dossier).count() + 1
            self.code = f"LIN-{count:03d}"

        if self.geometrie:
            target_srid = self.dossier.srid_projection if self.dossier else get_default_srid_for_geom(self.geometrie)
            geom_utm = self.geometrie.transform(target_srid, clone=True)
            self.longueur_metres = round(geom_utm.length, 1)

        super().save(*args, **kwargs)


# =============================================================================
# 4. SIGNALEMENTS DE DOMMAGES & ANOMALIES TERRAIN
# =============================================================================

class SignalementDommage(TimeStampedModel):
    """
    Signalement géolocalisé d'incident ou de dégradation (Eau, Voirie, Décharge, Foncier).
    Généralisé à l'ensemble des Dossiers territoriaux (Campus, Collectivité locale, Parcelle).
    """
    CAT_EAU = 'eau'
    CAT_ELECTRICITE = 'electricite'
    CAT_ROUTE = 'route'
    CAT_ASSAINISSEMENT = 'assainissement'
    CAT_ECLAIRAGE = 'eclairage'
    CAT_INFRASTRUCTURE = 'infrastructure'
    CAT_FONCIER = 'foncier'
    CAT_AUTRE = 'autre'

    CATEGORIES = [
        (CAT_EAU, 'Eau / Fuite'),
        (CAT_ELECTRICITE, 'Électricité / Câblage'),
        (CAT_ROUTE, 'Voirie / Piste endommagée'),
        (CAT_ASSAINISSEMENT, 'Assainissement / Déchets'),
        (CAT_ECLAIRAGE, 'Éclairage public défaillant'),
        (CAT_INFRASTRUCTURE, 'Bâtiment / Mur menaçant ruine'),
        (CAT_FONCIER, 'Litige foncier / Empiètement illégal'),
        (CAT_AUTRE, 'Autre anomalie'),
    ]

    STATUT_NOUVEAU = 'nouveau'
    STATUT_PRIS_EN_CHARGE = 'pris_en_charge'
    STATUT_EN_COURS = 'en_cours'
    STATUT_RESOLU = 'resolu'
    STATUT_REJETE = 'rejete'

    STATUTS = [
        (STATUT_NOUVEAU, 'Nouveau signalement'),
        (STATUT_PRIS_EN_CHARGE, 'Pris en charge par l\'équipe'),
        (STATUT_EN_COURS, 'Travaux / Intervention en cours'),
        (STATUT_RESOLU, 'Anomalie résolue'),
        (STATUT_REJETE, 'Signalement non fondé / Rejeté'),
    ]

    PRIORITE_BASSE = 'basse'
    PRIORITE_NORMALE = 'normale'
    PRIORITE_HAUTE = 'haute'
    PRIORITE_URGENTE = 'urgente'

    PRIORITES = [
        (PRIORITE_BASSE, 'Basse'),
        (PRIORITE_NORMALE, 'Normale'),
        (PRIORITE_HAUTE, 'Haute'),
        (PRIORITE_URGENTE, 'Urgente / Péril imminent'),
    ]

    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        related_name='signalements',
        verbose_name="Dossier territorial"
    )
    zone_secteur = models.ForeignKey(
        ZoneSecteur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signalements',
        verbose_name="Zone ou village concerné"
    )
    numero = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro de dossier d'incident"
    )
    titre = models.CharField(
        max_length=150,
        verbose_name="Intitulé de l'incident"
    )
    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIES,
        default=CAT_AUTRE,
        verbose_name="Nature du dommage"
    )
    priorite = models.CharField(
        max_length=20,
        choices=PRIORITES,
        default=PRIORITE_NORMALE,
        verbose_name="Niveau de priorité"
    )
    statut = models.CharField(
        max_length=30,
        choices=STATUTS,
        default=STATUT_NOUVEAU,
        verbose_name="État d'avancement"
    )
    description = models.TextField(
        verbose_name="Description détaillée du problème"
    )
    geometrie = models.PointField(
        srid=4326,
        verbose_name="Point GPS de l'incident"
    )
    photo = models.ImageField(
        upload_to='signalements/',
        blank=True,
        null=True,
        verbose_name="Photo de constatation"
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signalements_declares',
        verbose_name="Agent déclarant"
    )
    date_signalement = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date et heure du signalement"
    )
    date_resolution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de clôture"
    )
    commentaire_resolution = models.TextField(
        blank=True,
        verbose_name="Rapport d'intervention ou motif de clôture"
    )

    class Meta:
        verbose_name = "Signalement de dommage"
        verbose_name_plural = "Signalements de dommages"
        ordering = ['-date_signalement']

    def __str__(self):
        return f"{self.numero} — {self.titre} [{self.get_statut_display()}]"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().year
            count = SignalementDommage.objects.filter(dossier=self.dossier).count() + 1
            self.numero = f"SIG-{annee}-{count:04d}"

        # Détection automatique de la ZoneSecteur si le point est inclus dans un polygone
        if self.geometrie and not self.zone_secteur:
            zone_trouvee = ZoneSecteur.objects.filter(
                dossier=self.dossier,
                geometrie__contains=self.geometrie
            ).first()
            if zone_trouvee:
                self.zone_secteur = zone_trouvee

        super().save(*args, **kwargs)
