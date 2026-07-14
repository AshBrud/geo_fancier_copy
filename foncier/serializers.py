from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import (
    Espace, Batiment, FonctionBatiment,
    Terrain, EspaceVert, Voirie, PointInteret,
)


class EspaceSerializer(GeoFeatureModelSerializer):
    couleur = serializers.ReadOnlyField()
    superficie_ha = serializers.ReadOnlyField()
    type_display = serializers.CharField(source='get_type_espace_display', read_only=True)

    class Meta:
        model = Espace
        geo_field = 'geometrie'
        fields = ['id', 'nom', 'code', 'type_espace', 'type_display',
                  'superficie', 'superficie_ha', 'description', 'usage', 'couleur']


class BatimentSerializer(GeoFeatureModelSerializer):
    fonction_nom = serializers.CharField(source='fonction.nom', read_only=True)
    superficie_ha = serializers.ReadOnlyField()

    class Meta:
        model = Batiment
        geo_field = 'geometrie'
        fields = ['id', 'nom', 'code', 'fonction', 'fonction_nom', 'superficie',
                  'superficie_ha', 'etages', 'annee_construction',
                  'description', 'photo', 'est_actif']


class TerrainSerializer(GeoFeatureModelSerializer):
    superficie_ha = serializers.ReadOnlyField()

    class Meta:
        model = Terrain
        geo_field = 'geometrie'
        fields = ['id', 'nom', 'type_terrain', 'etat', 'superficie', 'superficie_ha', 'observation']


class EspaceVertSerializer(GeoFeatureModelSerializer):
    superficie_ha = serializers.ReadOnlyField()

    class Meta:
        model = EspaceVert
        geo_field = 'geometrie'
        fields = ['id', 'nom', 'type_espace_vert', 'etat', 'superficie', 'superficie_ha', 'observation']


class VoirieSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Voirie
        geo_field = 'geometrie'
        fields = ['id', 'nom', 'type_voirie', 'revetement', 'etat', 'longueur', 'observation']


class PointInteretSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = PointInteret
        geo_field = 'geometrie'
        fields = ['id', 'nom', 'categorie', 'observation']
