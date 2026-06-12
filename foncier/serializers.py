from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import Espace, Batiment, FonctionBatiment


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
                  'superficie_ha', 'etages', 'annee_construction', 'capacite',
                  'description', 'photo', 'est_actif']
