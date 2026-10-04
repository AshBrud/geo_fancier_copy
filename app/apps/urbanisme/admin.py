from django.contrib.gis import admin
from .models import NouvelleConstruction, HistoriqueConstruction


@admin.register(NouvelleConstruction)
class NouvelleConstructionAdmin(admin.GISModelAdmin):
    list_display = ['nom_projet', 'dossier', 'zone_secteur', 'type_construction', 'superficie_souhaitee', 'statut', 'date_demande']
    list_filter = ['dossier', 'statut', 'disponible']
    search_fields = ['nom_projet', 'dossier__nom']
    autocomplete_fields = ['dossier', 'zone_secteur']



@admin.register(HistoriqueConstruction)
class HistoriqueConstructionAdmin(admin.ModelAdmin):
    list_display = ['unite_batie', 'type_travaux', 'date_debut', 'date_fin']
    list_filter = ['type_travaux', 'date_debut']
    autocomplete_fields = ['unite_batie']

