from django.conf import settings
from django.contrib.gis.db import models

from .models_mission import Mission


class Orthophoto(models.Model):
    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='orthophotos',
        verbose_name="Dossier territorial",
    )
    mission = models.ForeignKey(
        Mission, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orthophotos', verbose_name='Mission associée',
    )
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
        help_text='Format : /static/tiles/{z}/{x}/{y}.png ou URL WebODM',
    )
    tuiles_locales = models.BooleanField(
        default=False,
        verbose_name='Tuiles générées localement',
        help_text="Si activé, tiles_url pointe vers des tuiles stockées sur ce serveur "
                   "(indépendantes de WebODM) plutôt que vers WebODM directement.",
    )
    description = models.TextField(blank=True)
    valide = models.BooleanField(default=False, verbose_name='Validée')
    date_validation = models.DateTimeField(blank=True, null=True, verbose_name='Date de validation')
    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orthophotos_validees', verbose_name='Validée par',
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orthophoto'
        verbose_name_plural = 'Orthophotos'
        ordering = ['-date_prise']

    def __str__(self):
        return f"{self.nom} - {self.date_prise}"

    @property
    def superficie_ha(self):
        if not self.emprise:
            return None
        try:
            geom_utm = self.emprise.transform(32628, clone=True)
            return round(geom_utm.area / 10000, 4)
        except Exception:
            return None
