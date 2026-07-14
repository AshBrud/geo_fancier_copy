from django.contrib.gis import admin
from .models import Orthophoto, Mission, PhotoDrone, FluxVideo


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date_vol', 'operateur', 'statut', 'nb_photos']
    list_filter = ['statut', 'date_vol']
    search_fields = ['nom', 'operateur']


@admin.register(Orthophoto)
class OrthophotoAdmin(admin.ModelAdmin):
    list_display = ['nom', 'mission', 'date_prise', 'operateur', 'resolution', 'valide', 'systeme_proj']
    list_filter = ['date_prise', 'valide', 'operateur']
    search_fields = ['nom', 'operateur', 'description']


@admin.register(PhotoDrone)
class PhotoDroneAdmin(admin.ModelAdmin):
    list_display = ['nom', 'mission', 'date_capture', 'operateur']
    list_filter = ['date_capture']
    search_fields = ['nom', 'operateur']


@admin.register(FluxVideo)
class FluxVideoAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date_enregistrement', 'operateur', 'duree_secondes']
    list_filter = ['date_enregistrement']
    search_fields = ['nom', 'operateur']
