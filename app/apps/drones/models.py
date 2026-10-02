from django.contrib.gis.db import models
from django.conf import settings


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
        verbose_name="Dossier territorial"
    )
    nom = models.CharField(max_length=200, verbose_name='Nom de la mission')
    date_vol = models.DateField(verbose_name='Date du vol')
    operateur = models.CharField(max_length=200, blank=True, verbose_name='Opérateur')
    drone_utilise = models.CharField(max_length=200, blank=True, verbose_name='Drone utilisé')
    altitude = models.FloatField(blank=True, null=True, verbose_name='Altitude de vol (m)')
    duree_minutes = models.FloatField(blank=True, null=True, verbose_name='Durée du vol (min)')
    superficie_prevue = models.FloatField(blank=True, null=True, verbose_name='Superficie prévue (ha)')
    statut = models.CharField(
        max_length=20, choices=STATUTS, default=STATUT_ATTENTE,
        verbose_name='Statut',
    )
    notes = models.TextField(blank=True, verbose_name='Observations')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

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


class Orthophoto(models.Model):
    dossier = models.ForeignKey(
        'dossiers.Dossier',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='orthophotos',
        verbose_name="Dossier territorial"
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
        help_text='Format : /static/tiles/{z}/{x}/{y}.png ou URL WebODM'
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
