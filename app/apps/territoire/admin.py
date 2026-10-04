from django.contrib import admin
from .models import SuiviTravaux


@admin.register(SuiviTravaux)
class SuiviTravauxAdmin(admin.ModelAdmin):
    list_display = ['construction', 'statut', 'maitre_ouvrage', 'date_debut', 'date_fin_prevue', 'date_creation']
    list_filter = ['statut', 'date_creation']
    search_fields = ['construction__nom_projet', 'observations']
    autocomplete_fields = ['maitre_ouvrage']

