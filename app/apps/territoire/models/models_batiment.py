from django.contrib.gis.db import models


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
