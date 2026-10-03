from django.contrib.gis.db import models
from django.db.models import Sum


def superficie_campus_totale():
    """Superficie totale du périmètre d'étude = superficie du polygone Campus."""
    campus = Campus.objects.first()
    return campus.superficie or 0 if campus else 0


class Campus(models.Model):
    """
    Polygone unique représentant les limites du campus.
    Sert uniquement de référence cartographique : il ne représente pas un
    espace foncier ordinaire et n'est jamais inclus dans les calculs de
    superficie des statistiques (voir superficie_campus_totale()).
    """
    nom = models.CharField(max_length=200, default='Campus UAD Bambey', verbose_name='Nom')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    description = models.TextField(blank=True, verbose_name='Description')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Campus'
        verbose_name_plural = 'Campus'

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

    @property
    def superficie_batiments(self):
        if not self.geometrie:
            return 0.0
        from territoire.models import Batiment
        return Batiment.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_terrains_sportifs(self):
        """Terrains de type sportif uniquement — un terrain nu/réserve foncière n'est pas une occupation du sol."""
        if not self.geometrie:
            return 0.0
        from territoire.models import Terrain
        return Terrain.objects.filter(
            geometrie__intersects=self.geometrie, type_terrain__icontains='sport'
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_espaces_verts(self):
        if not self.geometrie:
            return 0.0
        from territoire.models import EspaceVert
        return EspaceVert.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_voiries(self):
        return 0.0

    @property
    def superficie_occupee(self):
        """Bâtiments + terrains sportifs + espaces verts + voiries (emprise au sol)."""
        return (
            self.superficie_batiments
            + self.superficie_terrains_sportifs
            + self.superficie_espaces_verts
            + self.superficie_voiries
        )

    @property
    def superficie_reservee(self):
        """Superficie des sous-espaces de type Réservé rattachés au campus (non occupés)."""
        from territoire.models import Espace
        return self.sous_espaces.filter(type_espace=Espace.TYPE_RESERVE).aggregate(
            t=Sum('superficie')
        )['t'] or 0.0

    @property
    def superficie_libre(self):
        """Superficie du campus − occupée (bâti/terrains sportifs/espaces verts/voiries) − réservée."""
        return max(0.0, (self.superficie or 0.0) - self.superficie_occupee - self.superficie_reservee)

    @property
    def taux_occupation(self):
        return round(self.superficie_occupee / self.superficie * 100, 1) if self.superficie else 0.0
