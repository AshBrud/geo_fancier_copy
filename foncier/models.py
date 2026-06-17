from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import Area
from django.contrib.gis.measure import A
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# Superficie officielle du campus UAD Bambey (55 ha)
SUPERFICIE_CAMPUS_M2 = 550000


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
    capacite = models.IntegerField(blank=True, null=True, verbose_name='Capacité (personnes)')
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
