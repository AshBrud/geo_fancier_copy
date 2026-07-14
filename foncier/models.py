from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import Area
from django.contrib.gis.measure import A
from django.db.models import Sum
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

# Superficie officielle du campus UAD Bambey (52 ha)
SUPERFICIE_CAMPUS_M2 = 520000


class Espace(models.Model):
    TYPE_LIBRE = 'libre'
    TYPE_OCCUPE = 'occupe'
    TYPE_RESERVE = 'reserve'
    TYPE_ROUTE = 'route'
    TYPES = [
        (TYPE_LIBRE, 'Espace libre'),
        (TYPE_OCCUPE, 'Espace occupé'),
        (TYPE_RESERVE, 'Espace réservé'),
        (TYPE_ROUTE, 'Route / Voie'),
    ]

    COULEURS = {
        TYPE_LIBRE: '#16A34A',
        TYPE_OCCUPE: '#DC2626',
        TYPE_RESERVE: '#F59E0B',
        TYPE_ROUTE: '#6B7280',
    }

    nom = models.CharField(max_length=200, verbose_name='Nom')
    code = models.CharField(max_length=30, unique=True, verbose_name='Code')
    type_espace = models.CharField(max_length=20, choices=TYPES, verbose_name='Type')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    taux_occupation = models.FloatField(
        default=60.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(100.0)],
        verbose_name="Taux d'occupation max (%)",
        help_text="Pourcentage de la superficie effectivement constructible (le reste est réservé aux voiries, espaces verts, parkings…)",
    )
    description = models.TextField(blank=True, verbose_name='Description')
    usage = models.CharField(max_length=200, blank=True, verbose_name='Usage')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Espace'
        verbose_name_plural = 'Espaces'
        ordering = ['nom']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def save(self, *args, **kwargs):
        if self.geometrie:
            # Superficie en m² via transformation en projection métrique locale (UTM 28N)
            from django.contrib.gis.geos import GEOSGeometry
            geom_utm = self.geometrie.transform(32628, clone=True)
            self.superficie = round(geom_utm.area, 2)
        super().save(*args, **kwargs)

    @property
    def couleur(self):
        return self.COULEURS.get(self.type_espace, '#6B7280')

    @property
    def superficie_ha(self):
        if self.superficie:
            return round(self.superficie / 10000, 4)
        return None

    @property
    def superficie_batie(self):
        """Superficie cumulée des bâtiments déjà construits dans cet espace."""
        if not self.geometrie:
            return 0.0
        return Batiment.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0


class FonctionBatiment(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Fonction de bâtiment'
        verbose_name_plural = 'Fonctions de bâtiments'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Batiment(models.Model):
    nom = models.CharField(max_length=200, verbose_name='Nom')
    code = models.CharField(max_length=30, unique=True, verbose_name='Code')
    fonction = models.ForeignKey(
        FonctionBatiment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Fonction'
    )
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    etages = models.PositiveIntegerField(default=1, verbose_name='Nombre d\'étages')
    annee_construction = models.IntegerField(blank=True, null=True, verbose_name='Année de construction')
    description = models.TextField(blank=True, verbose_name='Description')
    photo = models.ImageField(upload_to='batiments/', blank=True, null=True, verbose_name='Photo')
    est_actif = models.BooleanField(default=True, verbose_name='Actif')
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bâtiment'
        verbose_name_plural = 'Bâtiments'
        ordering = ['nom']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def save(self, *args, **kwargs):
        if self.geometrie:
            geom_utm = self.geometrie.transform(32628, clone=True)
            self.superficie = round(geom_utm.area, 2)
        super().save(*args, **kwargs)

    @property
    def superficie_ha(self):
        if self.superficie:
            return round(self.superficie / 10000, 4)
        return None


class Terrain(models.Model):
    """Terrain nu ou réserve foncière, importé depuis les levés QGIS/PostGIS."""
    nom = models.CharField(max_length=200, verbose_name='Nom')
    type_terrain = models.CharField(max_length=100, blank=True, verbose_name='Type')
    etat = models.CharField(max_length=100, blank=True, verbose_name='État')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    observation = models.TextField(blank=True, verbose_name='Observation')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Terrain'
        verbose_name_plural = 'Terrains'
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if self.geometrie:
            geom_utm = self.geometrie.transform(32628, clone=True)
            self.superficie = round(geom_utm.area, 2)
        super().save(*args, **kwargs)

    @property
    def superficie_ha(self):
        if self.superficie:
            return round(self.superficie / 10000, 4)
        return None


class EspaceVert(models.Model):
    """Espace vert (pelouse, jardin, zone plantée), importé depuis les levés QGIS/PostGIS."""
    nom = models.CharField(max_length=200, verbose_name='Nom')
    type_espace_vert = models.CharField(max_length=100, blank=True, verbose_name='Type')
    etat = models.CharField(max_length=100, blank=True, verbose_name='État')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    observation = models.TextField(blank=True, verbose_name='Observation')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Espace vert'
        verbose_name_plural = 'Espaces verts'
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if self.geometrie:
            geom_utm = self.geometrie.transform(32628, clone=True)
            self.superficie = round(geom_utm.area, 2)
        super().save(*args, **kwargs)

    @property
    def superficie_ha(self):
        if self.superficie:
            return round(self.superficie / 10000, 4)
        return None


class Voirie(models.Model):
    """Route, allée ou piste du campus, importée depuis les levés QGIS/PostGIS."""
    nom = models.CharField(max_length=200, verbose_name='Nom')
    type_voirie = models.CharField(max_length=100, blank=True, verbose_name='Type')
    revetement = models.CharField(max_length=100, blank=True, verbose_name='Revêtement')
    etat = models.CharField(max_length=100, blank=True, verbose_name='État')
    geometrie = models.MultiLineStringField(srid=4326, verbose_name='Géométrie')
    longueur = models.FloatField(blank=True, null=True, verbose_name='Longueur (m)')
    observation = models.TextField(blank=True, verbose_name='Observation')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Voirie'
        verbose_name_plural = 'Voiries'
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if self.geometrie:
            geom_utm = self.geometrie.transform(32628, clone=True)
            self.longueur = round(geom_utm.length, 2)
        super().save(*args, **kwargs)


class PointInteret(models.Model):
    """Point d'intérêt du campus (entrée, parking, terrain de sport…)."""
    nom = models.CharField(max_length=200, verbose_name='Nom')
    categorie = models.CharField(max_length=100, blank=True, verbose_name='Catégorie')
    geometrie = models.PointField(srid=4326, verbose_name='Géométrie')
    observation = models.TextField(blank=True, verbose_name='Observation')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Point d'intérêt"
        verbose_name_plural = "Points d'intérêt"
        ordering = ['nom']

    def __str__(self):
        return self.nom


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
        'constructions.NouvelleConstruction',
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
