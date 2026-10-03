from django.contrib.gis.db import models


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
