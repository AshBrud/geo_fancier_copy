from django.contrib.gis import admin
from .models import MissionDrone, Orthophoto


@admin.register(MissionDrone)
class MissionDroneAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'date_mission', 'operateur', 'statut']
    list_filter = ['statut', 'date_mission']


@admin.register(Orthophoto)
class OrthophotoAdmin(admin.ModelAdmin):
    list_display = ['nom', 'mission', 'date_prise', 'resolution']
