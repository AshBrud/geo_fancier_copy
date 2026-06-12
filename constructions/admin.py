from django.contrib.gis import admin
from .models import NouvelleConstruction, HistoriqueConstruction


@admin.register(NouvelleConstruction)
class NouvelleConstructionAdmin(admin.GISModelAdmin):
    list_display = ['nom_projet', 'type_construction', 'superficie_souhaitee', 'statut', 'date_demande']
    list_filter = ['statut', 'disponible']


@admin.register(HistoriqueConstruction)
class HistoriqueConstructionAdmin(admin.ModelAdmin):
    list_display = ['batiment', 'type_travaux', 'date_debut', 'date_fin']
    list_filter = ['type_travaux', 'date_debut']
