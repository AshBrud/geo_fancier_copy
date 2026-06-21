from django.contrib.gis.db import models


class Orthophoto(models.Model):
    nom = models.CharField(max_length=200, verbose_name='Nom')
    fichier = models.FileField(upload_to='orthophotos/', verbose_name='Fichier (GeoTIFF, PNG, JPEG)')
    date_prise = models.DateField(verbose_name='Date de prise de vue')
    operateur = models.CharField(max_length=200, blank=True, verbose_name='Opérateur')
    resolution = models.FloatField(blank=True, null=True, verbose_name='Résolution (cm/px)')
    emprise = models.PolygonField(srid=4326, blank=True, null=True, verbose_name='Emprise géographique')
    systeme_proj = models.CharField(max_length=200, blank=True, verbose_name='Système de projection')
    largeur_px = models.IntegerField(blank=True, null=True, verbose_name='Largeur (px)')
    hauteur_px = models.IntegerField(blank=True, null=True, verbose_name='Hauteur (px)')
    tiles_url = models.CharField(
        max_length=500, blank=True,
        verbose_name='URL tuiles XYZ (WebODM)',
        help_text='Format : /static/tiles/{z}/{x}/{y}.png ou URL WebODM'
    )
    description = models.TextField(blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orthophoto'
        verbose_name_plural = 'Orthophotos'
        ordering = ['-date_prise']

    def __str__(self):
        return f"{self.nom} - {self.date_prise}"
