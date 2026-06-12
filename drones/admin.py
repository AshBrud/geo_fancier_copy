from django.contrib.gis import admin
from .models import MissionDrone, Orthophoto


@admin.register(MissionDrone)
class MissionDroneAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'date_mission', 'operateur', 'statut', 'tiles_url']
    list_filter = ['statut', 'date_mission']
    fieldsets = [
        (None, {'fields': ['nom', 'date_mission', 'operateur', 'drone_utilise', 'statut']}),
        ('Paramètres de vol', {'fields': ['altitude_vol', 'recouvrement', 'zone_couverte']}),
        ('Orthophoto (WebODM)', {'fields': ['tiles_url'], 'description': 'URL des tuiles XYZ générées par WebODM/QGIS'}),
        ('Informations', {'fields': ['description']}),
    ]


@admin.register(Orthophoto)
class OrthophotoAdmin(admin.ModelAdmin):
    list_display = ['nom', 'mission', 'date_prise', 'resolution']
