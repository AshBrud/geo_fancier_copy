from django.contrib.gis import admin
from .models import Espace, Batiment, FonctionBatiment


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
