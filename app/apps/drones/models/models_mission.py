from django.contrib.gis.db import models


class Mission(models.Model):
    STATUT_ATTENTE = 'attente'
    STATUT_TRAITEMENT = 'traitement'
    STATUT_TRAITEE = 'traitee'
    STATUT_INTEGREE = 'integree'

    STATUTS = [
        (STATUT_ATTENTE, 'En attente'),
        (STATUT_TRAITEMENT, 'En traitement'),
        (STATUT_TRAITEE, 'Traitée'),
        (STATUT_INTEGREE, 'Intégrée'),
    ]

    BADGE_COULEURS = {
        STATUT_ATTENTE: 'secondary',
        STATUT_TRAITEMENT: 'warning',
        STATUT_TRAITEE: 'info',
        STATUT_INTEGREE: 'success',
    }

    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='missions_drone',
        verbose_name="Dossier territorial",
    )
    nom = models.CharField(max_length=200, verbose_name='Nom de la mission')
    date_vol = models.DateField(verbose_name='Date du vol')
    operateur = models.CharField(max_length=200, blank=True, verbose_name='Opérateur')
    drone_utilise = models.CharField(max_length=200, blank=True, verbose_name='Drone utilisé')
    altitude = models.FloatField(blank=True, null=True, verbose_name='Altitude de vol (m)')
    duree_minutes = models.FloatField(blank=True, null=True, verbose_name='Durée du vol (min)')
    superficie_prevue = models.FloatField(blank=True, null=True, verbose_name='Superficie prévue (ha)')
    emprise = models.PolygonField(
        srid=4326, blank=True, null=True,
        verbose_name="Zone de vol (Emprise autorisée)",
    )
    trajectoire = models.LineStringField(
        srid=4326, blank=True, null=True,
        verbose_name="Trajectoire de vol planifiée",
    )
    statut = models.CharField(
        max_length=20, choices=STATUTS, default=STATUT_ATTENTE,
        verbose_name='Statut',
    )
    notes = models.TextField(blank=True, verbose_name='Observations')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.emprise and not self.superficie_prevue:
            try:
                geom_utm = self.emprise.transform(32628, clone=True)
                self.superficie_prevue = round(geom_utm.area / 10000, 2)
            except Exception:
                pass
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Mission drone'
        verbose_name_plural = 'Missions drone'
        ordering = ['-date_vol']

    def __str__(self):
        return f"{self.nom} ({self.get_statut_display()})"

    @property
    def badge_couleur(self):
        return self.BADGE_COULEURS.get(self.statut, 'secondary')

    @property
    def nb_photos(self):
        return self.photos.count()

    @property
    def a_orthophoto(self):
        return self.orthophotos.exists()
