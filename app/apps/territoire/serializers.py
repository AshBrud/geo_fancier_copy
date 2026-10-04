from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from dossiers.models import ZoneSecteur, UniteBatie, ReseauLineaire


class ZoneSecteurSerializer(GeoFeatureModelSerializer):
    superficie_ha = serializers.ReadOnlyField()
    superficie_m2 = serializers.ReadOnlyField()
    surface_batie_m2 = serializers.ReadOnlyField()
    nb_unites_baties = serializers.ReadOnlyField()
    couleur = serializers.ReadOnlyField()
    type_display = serializers.CharField(source='get_type_zone_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = ZoneSecteur
        geo_field = 'geometrie'
        fields = [
            'id', 'nom', 'code', 'type_zone', 'type_display',
            'statut', 'statut_display', 'superficie_m2', 'superficie_ha',
            'surface_batie_m2', 'nb_unites_baties', 'population_estimee',
            'couleur', 'description'
        ]


class UniteBatieSerializer(GeoFeatureModelSerializer):
    type_display = serializers.CharField(source='get_type_bati_display', read_only=True)
    statut_occupation_display = serializers.CharField(source='get_statut_occupation_display', read_only=True)
    superficie_ha = serializers.ReadOnlyField()
    emprise_sol_m2 = serializers.ReadOnlyField()

    class Meta:
        model = UniteBatie
        geo_field = 'geometrie'
        fields = [
            'id', 'nom', 'code', 'type_bati', 'type_display',
            'statut_occupation', 'statut_occupation_display',
            'superficie_m2', 'emprise_sol_m2', 'superficie_ha',
            'etages', 'annee_construction',
            'description', 'photo', 'est_actif',
            'zone_secteur'
        ]


class ReseauLineaireSerializer(GeoFeatureModelSerializer):
    type_display = serializers.CharField(source='get_type_voie_display', read_only=True)
    longueur_km = serializers.ReadOnlyField()
    couleur = serializers.ReadOnlyField()

    class Meta:
        model = ReseauLineaire
        geo_field = 'geometrie'
        fields = [
            'id', 'nom', 'code', 'type_voie', 'type_display',
            'etat_chaussee', 'largeur_estimee_m',
            'longueur_metres', 'longueur_km', 'couleur', 'description'
        ]
