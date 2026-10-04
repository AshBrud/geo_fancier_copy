from django.contrib.gis.db import models

from .models_mission import Mission


class FluxVideo(models.Model):
    nom = models.CharField(max_length=200, verbose_name='Nom')
    fichier = models.FileField(upload_to='flux_videos/', verbose_name='Fichier vidéo')
    date_enregistrement = models.DateTimeField(auto_now_add=True, verbose_name='Date')
    duree_secondes = models.IntegerField(null=True, blank=True, verbose_name='Durée (s)')
    taille_octets = models.BigIntegerField(null=True, blank=True, verbose_name='Taille (octets)')
    operateur = models.CharField(max_length=100, blank=True, verbose_name='Opérateur')
    source_rtsp = models.CharField(max_length=500, blank=True, verbose_name='Source RTSP')

    class Meta:
        ordering = ['-date_enregistrement']
        verbose_name = 'Flux vidéo'
        verbose_name_plural = 'Flux vidéos'

    def __str__(self):
        return self.nom

    @property
    def taille_mb(self):
        if self.taille_octets:
            return round(self.taille_octets / 1048576, 1)
        return None

    @property
    def duree_formatee(self):
        if not self.duree_secondes:
            return '—'
        m, s = divmod(self.duree_secondes, 60)
        h, m = divmod(m, 60)
        if h:
            return f'{h:02d}:{m:02d}:{s:02d}'
        return f'{m:02d}:{s:02d}'


class PhotoDrone(models.Model):
    mission = models.ForeignKey(
        Mission, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='photos', verbose_name='Mission associée',
    )
    nom = models.CharField(max_length=200, verbose_name='Nom')
    image = models.ImageField(upload_to='photos_drone/', verbose_name='Image')
    date_capture = models.DateTimeField(auto_now_add=True, verbose_name='Date de capture')
    operateur = models.CharField(max_length=100, blank=True, verbose_name='Opérateur')
    notes = models.TextField(blank=True, verbose_name='Notes')

    class Meta:
        ordering = ['-date_capture']
        verbose_name = 'Photo drone'
        verbose_name_plural = 'Photos drone'

    def __str__(self):
        return self.nom
