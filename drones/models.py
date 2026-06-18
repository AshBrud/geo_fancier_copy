from django.contrib.gis.db import models
from django.conf import settings


class MissionDrone(models.Model):
    STATUT_PLANIFIE = 'planifie'
    STATUT_REALISE = 'realise'
    STATUT_TRAITE = 'traite'

    STATUTS = [
        (STATUT_PLANIFIE, 'Planifiée'),
        (STATUT_REALISE, 'Réalisée'),
        (STATUT_TRAITE, 'Traitée'),
    ]

    nom = models.CharField(max_length=200, verbose_name='Nom de la mission')
    date_mission = models.DateField(verbose_name='Date de la mission')
    operateur = models.CharField(max_length=200, verbose_name='Opérateur')
    drone_utilise = models.CharField(max_length=100, blank=True, verbose_name='Drone utilisé')
    zone_couverte = models.PolygonField(srid=4326, blank=True, null=True, verbose_name='Zone couverte')
    altitude_vol = models.FloatField(blank=True, null=True, verbose_name='Altitude (m)')
    recouvrement = models.FloatField(blank=True, null=True, verbose_name='Taux de recouvrement (%)')
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_PLANIFIE)
    description = models.TextField(blank=True, verbose_name='Description')
    tiles_url = models.CharField(
        max_length=500, blank=True,
        verbose_name='URL tuiles XYZ (WebODM)',
        help_text='Format : /static/tiles/mission/{z}/{x}/{y}.png ou URL WebODM'
    )
    fichier_kml = models.FileField(
        upload_to='missions/kml/', blank=True, null=True,
        verbose_name='Fichier KML/KMZ/GPX',
        help_text='Importer automatiquement la zone couverte depuis un fichier KML, KMZ ou GPX'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mission Drone'
        verbose_name_plural = 'Missions Drones'
        ordering = ['-date_mission']

    def __str__(self):
        return f"{self.nom} ({self.date_mission})"


class Orthophoto(models.Model):
    mission = models.ForeignKey(
        MissionDrone, on_delete=models.CASCADE,
        related_name='orthophotos', verbose_name='Mission'
    )
    nom = models.CharField(max_length=200, verbose_name='Nom')
    fichier = models.FileField(upload_to='orthophotos/', verbose_name='Fichier (GeoTIFF, PNG, JPEG)')
    date_prise = models.DateField(verbose_name='Date de prise de vue')
    resolution = models.FloatField(blank=True, null=True, verbose_name='Résolution (cm/px)')
    emprise = models.PolygonField(srid=4326, blank=True, null=True, verbose_name='Emprise géographique')
    systeme_proj = models.CharField(max_length=200, blank=True, verbose_name='Système de projection')
    largeur_px = models.IntegerField(blank=True, null=True, verbose_name='Largeur (px)')
    hauteur_px = models.IntegerField(blank=True, null=True, verbose_name='Hauteur (px)')
    description = models.TextField(blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orthophoto'
        verbose_name_plural = 'Orthophotos'
        ordering = ['-date_prise']

    def __str__(self):
        return f"{self.nom} - {self.date_prise}"
