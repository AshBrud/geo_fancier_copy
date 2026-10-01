from django.contrib.gis import admin

from .models import (Commune, HistoriqueSignalement, Maison, Notification, OrthophotoCommune,
                     Piste, Signalement, Village)


@admin.register(Commune)
class CommuneAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'departement', 'region', 'superficie']


@admin.register(Village)
class VillageAdmin(admin.GISModelAdmin):
    list_display = ['code', 'nom', 'superficie']
    search_fields = ['nom', 'code']


@admin.register(Maison)
class MaisonAdmin(admin.GISModelAdmin):
    list_display = ['code', 'village', 'statut_occupation', 'superficie']
    list_filter = ['statut_occupation', 'village']
    search_fields = ['code', 'village__nom']


@admin.register(OrthophotoCommune)
class OrthophotoCommuneAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'resolution', 'superficie', 'zoom_max', 'date_ajout']
    readonly_fields = ['tiles_url', 'fichier', 'superficie']


@admin.register(Piste)
class PisteAdmin(admin.GISModelAdmin):
    list_display = ['nom', 'type_voie', 'longueur']
    list_filter = ['type_voie']


class HistoriqueInline(admin.TabularInline):
    model = HistoriqueSignalement
    extra = 0
    readonly_fields = ['ancien_statut', 'nouveau_statut', 'date_changement', 'utilisateur', 'commentaire']
    can_delete = False


@admin.register(Signalement)
class SignalementAdmin(admin.GISModelAdmin):
    list_display = ['numero', 'titre', 'categorie', 'village', 'priorite', 'statut', 'date_signalement']
    list_filter = ['statut', 'categorie', 'priorite', 'village']
    search_fields = ['titre', 'description']
    # Le statut évolue uniquement via la fiche (historique + notification)
    readonly_fields = ['statut']
    inlines = [HistoriqueInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['destinataire', 'message', 'lue', 'created_at']
    list_filter = ['lue']
