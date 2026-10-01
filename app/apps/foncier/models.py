from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import Area
from django.contrib.gis.measure import A
from django.db.models import Sum
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings


def superficie_campus_totale():
    """Superficie totale du périmètre d'étude = superficie du polygone Campus."""
    campus = Campus.objects.first()
    return campus.superficie or 0 if campus else 0


class Campus(models.Model):
    """
    Polygone unique représentant les limites du campus.
    Sert uniquement de référence cartographique : il ne représente pas un
    espace foncier ordinaire et n'est jamais inclus dans les calculs de
    superficie des statistiques (voir superficie_campus_totale()).
    """
    nom = models.CharField(max_length=200, default='Campus UAD Bambey', verbose_name='Nom')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    description = models.TextField(blank=True, verbose_name='Description')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campus'

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

    @property
    def superficie_batiments(self):
        if not self.geometrie:
            return 0.0
        return Batiment.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_terrains_sportifs(self):
        """Terrains de type sportif uniquement — un terrain nu/réserve foncière
        n'est pas une occupation du sol."""
        if not self.geometrie:
            return 0.0
        return Terrain.objects.filter(
            geometrie__intersects=self.geometrie, type_terrain__icontains='sport'
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_espaces_verts(self):
        if not self.geometrie:
            return 0.0
        return EspaceVert.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_voiries(self):
        """Emprise au sol des voiries. Le modèle Voirie stocke actuellement une
        géométrie linéaire (MultiLineString, longueur en m) et non un polygone
        d'emprise : tant qu'aucune superficie surfacique n'est disponible, cette
        couche contribue pour 0 m² (branché ici pour s'activer automatiquement
        le jour où une géométrie/superficie polygonale sera ajoutée au modèle)."""
        return 0.0

    @property
    def superficie_occupee(self):
        """Bâtiments + terrains sportifs + espaces verts + voiries (emprise au sol)."""
        return (
            self.superficie_batiments
            + self.superficie_terrains_sportifs
            + self.superficie_espaces_verts
            + self.superficie_voiries
        )

    @property
    def superficie_reservee(self):
        """Superficie des sous-espaces de type Réservé rattachés au campus (non occupés)."""
        return self.sous_espaces.filter(type_espace=Espace.TYPE_RESERVE).aggregate(
            t=Sum('superficie')
        )['t'] or 0.0

    @property
    def superficie_libre(self):
        """Superficie du campus − occupée (bâti/terrains sportifs/espaces verts/voiries) − réservée."""
        return max(0.0, (self.superficie or 0.0) - self.superficie_occupee - self.superficie_reservee)

    @property
    def taux_occupation(self):
        return round(self.superficie_occupee / self.superficie * 100, 1) if self.superficie else 0.0


class Espace(models.Model):
    """Sous-espace foncier (Libre ou Réservé) rattaché au Campus."""
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
    # Types proposés à la création manuelle d'un sous-espace. TYPE_OCCUPE est
    # positionné automatiquement par le workflow de construction (voir
    # constructions/signals.py) et ne doit jamais être choisi à la main.
    TYPES_SOUS_ESPACE = [
        (TYPE_LIBRE, 'Espace libre'),
        (TYPE_RESERVE, 'Espace réservé'),
    ]

    COULEURS = {
        TYPE_LIBRE: '#16A34A',
        TYPE_OCCUPE: '#DC2626',
        TYPE_RESERVE: '#F59E0B',
        TYPE_ROUTE: '#6B7280',
    }

    campus = models.ForeignKey(
        Campus, related_name='sous_espaces', on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Campus',
    )
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

    def clean(self):
        if not self.geometrie or not self.campus_id:
            return
        campus = self.campus
        if campus.geometrie and not campus.geometrie.contains(self.geometrie):
            raise ValidationError(
                "Ce sous-espace doit être entièrement contenu dans les limites du Campus."
            )
        autres = Espace.objects.filter(campus=self.campus).exclude(pk=self.pk)
        for autre in autres:
            if autre.geometrie and self.geometrie.intersects(autre.geometrie) \
                    and not self.geometrie.touches(autre.geometrie):
                raise ValidationError(
                    f"Ce polygone chevauche le sous-espace « {autre.nom} ». "
                    "Les sous-espaces ne doivent pas se superposer (double comptage)."
                )

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

    @property
    def superficie_terrains(self):
        """Superficie cumulée des terrains délimités dans cet espace."""
        if not self.geometrie:
            return 0.0
        return Terrain.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_espaces_verts(self):
        """Superficie cumulée des espaces verts délimités dans cet espace."""
        if not self.geometrie:
            return 0.0
        return EspaceVert.objects.filter(
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
    code = models.CharField(max_length=30, unique=True, null=True, blank=True, verbose_name='Code')
    description = models.TextField(blank=True, verbose_name='Description')
    type_terrain = models.CharField(max_length=100, blank=True, verbose_name='Type')
    etat = models.CharField(max_length=100, blank=True, verbose_name='État')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    photo = models.ImageField(upload_to='terrains/', blank=True, null=True, verbose_name='Photo')
    est_actif = models.BooleanField(default=True, verbose_name='Actif')
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
    code = models.CharField(max_length=30, unique=True, null=True, blank=True, verbose_name='Code')
    description = models.TextField(blank=True, verbose_name='Description')
    type_espace_vert = models.CharField(max_length=100, blank=True, verbose_name='Type')
    etat = models.CharField(max_length=100, blank=True, verbose_name='État')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    photo = models.ImageField(upload_to='espaces_verts/', blank=True, null=True, verbose_name='Photo')
    est_actif = models.BooleanField(default=True, verbose_name='Actif')
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
    TYPE_PRINCIPALE = 'principale'
    TYPE_SECONDAIRE = 'secondaire'
    TYPE_PIETONNE   = 'pietonne'
    TYPE_PARKING    = 'parking'
    TYPES_VOIRIE = [
        (TYPE_PRINCIPALE, 'Voie principale'),
        (TYPE_SECONDAIRE, 'Voie secondaire'),
        (TYPE_PIETONNE,   'Allée piétonne'),
        (TYPE_PARKING,    'Parking'),
    ]

    nom = models.CharField(max_length=200, verbose_name='Nom')
    code = models.CharField(max_length=30, unique=True, null=True, blank=True, verbose_name='Code')
    description = models.TextField(blank=True, verbose_name='Description')
    type_voirie = models.CharField(
        max_length=20, choices=TYPES_VOIRIE, blank=True, verbose_name='Type'
    )
    revetement = models.CharField(max_length=100, blank=True, verbose_name='Revêtement')
    etat = models.CharField(max_length=100, blank=True, verbose_name='État')
    geometrie = models.MultiLineStringField(srid=4326, verbose_name='Géométrie')
    longueur = models.FloatField(blank=True, null=True, verbose_name='Longueur (m)')
    photo = models.ImageField(upload_to='voiries/', blank=True, null=True, verbose_name='Photo')
    est_actif = models.BooleanField(default=True, verbose_name='Actif')
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
