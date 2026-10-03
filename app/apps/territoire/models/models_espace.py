from django.contrib.gis.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from .models_campus import Campus


class Espace(models.Model):
    """Sous-espace foncier (Libre ou Réservé) rattaché au Campus."""
    TYPE_LIBRE = 'libre'
    TYPE_OCCUPE = 'occupe'
    TYPE_RESERVE = 'reserve'
    TYPE_ROUTE = 'route'
    TYPES = [
        (TYPE_LIBRE, 'Espace libre'),
        (TYPE_OCCUPE, 'Espace occupé'),
        (TYPE_RESERVE, 'Espace réservé'),
        (TYPE_ROUTE, 'Route / Voie'),
    ]

    TYPES_SOUS_ESPACE = [
        (TYPE_LIBRE, 'Espace libre'),
        (TYPE_RESERVE, 'Espace réservé'),
    ]

    COULEURS = {
        TYPE_LIBRE: '#16A34A',
        TYPE_OCCUPE: '#DC2626',
        TYPE_RESERVE: '#F59E0B',
        TYPE_ROUTE: '#6B7280',
    }

    campus = models.ForeignKey(
        Campus, related_name='sous_espaces', on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Campus',
    )
    nom = models.CharField(max_length=200, verbose_name='Nom')
    code = models.CharField(max_length=30, unique=True, verbose_name='Code')
    type_espace = models.CharField(max_length=20, choices=TYPES, verbose_name='Type')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    taux_occupation = models.FloatField(
        default=60.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(100.0)],
        verbose_name="Taux d'occupation max (%)",
        help_text="Pourcentage de la superficie effectivement constructible (le reste est réservé aux voiries, espaces verts, parkings…)",
    )
    description = models.TextField(blank=True, verbose_name='Description')
    usage = models.CharField(max_length=200, blank=True, verbose_name='Usage')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Espace'
        verbose_name_plural = 'Espaces'
        ordering = ['nom']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def clean(self):
        if not self.geometrie or not self.campus_id:
            return
        campus = self.campus
        if campus.geometrie and not campus.geometrie.contains(self.geometrie):
            raise ValidationError(
                "Ce sous-espace doit être entièrement contenu dans les limites du Campus."
            )
        autres = Espace.objects.filter(campus=self.campus).exclude(pk=self.pk)
        for autre in autres:
            if autre.geometrie and self.geometrie.intersects(autre.geometrie) \
                    and not self.geometrie.touches(autre.geometrie):
                raise ValidationError(
                    f"Ce polygone chevauche le sous-espace « {autre.nom} ». "
                    "Les sous-espaces ne doivent pas se superposer (double comptage)."
                )

    def save(self, *args, **kwargs):
        if self.geometrie:
            geom_utm = self.geometrie.transform(32628, clone=True)
            self.superficie = round(geom_utm.area, 2)
        super().save(*args, **kwargs)

    @property
    def couleur(self):
        return self.COULEURS.get(self.type_espace, '#6B7280')

    @property
    def superficie_ha(self):
        if self.superficie:
            return round(self.superficie / 10000, 4)
        return None

    @property
    def superficie_batie(self):
        """Superficie cumulée des bâtiments déjà construits dans cet espace."""
        if not self.geometrie:
            return 0.0
        from territoire.models import Batiment
        return Batiment.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_terrains(self):
        """Superficie cumulée des terrains délimités dans cet espace."""
        if not self.geometrie:
            return 0.0
        from territoire.models import Terrain
        return Terrain.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0

    @property
    def superficie_espaces_verts(self):
        """Superficie cumulée des espaces verts délimités dans cet espace."""
        if not self.geometrie:
            return 0.0
        from territoire.models import EspaceVert
        return EspaceVert.objects.filter(
            geometrie__intersects=self.geometrie
        ).aggregate(t=Sum('superficie'))['t'] or 0.0
