from django.contrib.gis.db import models


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
