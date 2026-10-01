from django.contrib.gis import admin
from .models import (
    Espace, Batiment, FonctionBatiment,
    Terrain, EspaceVert, Voirie, PointInteret,
)


@admin.register(Espace)
class EspaceAdmin(admin.GISModelAdmin):
    list_display = ['code', 'nom', 'type_espace', 'superficie', 'date_creation']
    list_filter = ['type_espace']
    search_fields = ['nom', 'code']


@admin.register(Batiment)
class BatimentAdmin(admin.GISModelAdmin):
    list_display = ['code', 'nom', 'fonction', 'etages', 'superficie', 'est_actif']
    list_filter = ['fonction', 'est_actif']
    search_fields = ['nom', 'code']


@admin.register(FonctionBatiment)
class FonctionBatimentAdmin(admin.ModelAdmin):
    list_display = ['nom']


@admin.register(Terrain)
class TerrainAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'type_terrain', 'etat', 'superficie']
    list_filter = ['type_terrain', 'etat']
    search_fields = ['nom']


@admin.register(EspaceVert)
class EspaceVertAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'type_espace_vert', 'etat', 'superficie']
    list_filter = ['type_espace_vert', 'etat']
    search_fields = ['nom']


@admin.register(Voirie)
class VoirieAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'type_voirie', 'revetement', 'etat', 'longueur']
    list_filter = ['type_voirie', 'etat']
    search_fields = ['nom']


@admin.register(PointInteret)
class PointInteretAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'categorie']
    list_filter = ['categorie']
    search_fields = ['nom']
