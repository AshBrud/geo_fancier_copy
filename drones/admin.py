from django.contrib.gis import admin
from .models import Orthophoto


@admin.register(Orthophoto)
class OrthophotoAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date_prise', 'operateur', 'resolution', 'systeme_proj']
    list_filter  = ['date_prise', 'operateur']
    search_fields = ['nom', 'operateur', 'description']
