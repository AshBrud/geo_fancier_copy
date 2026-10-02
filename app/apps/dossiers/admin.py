from django.contrib.gis import admin
from .models import (
    Dossier,
    DossierMembership,
    ZoneSecteur,
    UniteBatie,
    ReseauLineaire,
    SignalementDommage,
)


class DossierMembershipInline(admin.TabularInline):
    model = DossierMembership
    extra = 1
    fields = ('user', 'role', 'assigned_by', 'date_creation')
    readonly_fields = ('date_creation',)
    autocomplete_fields = ('user', 'assigned_by')


class ZoneSecteurInline(admin.TabularInline):
    model = ZoneSecteur
    extra = 0
    fields = ('code', 'nom', 'type_zone', 'superficie_ha', 'statut')
    readonly_fields = ('superficie_ha',)
    show_change_link = True


@admin.register(Dossier)
class DossierAdmin(admin.GISModelAdmin):
    list_display = (
        'nom',
        'type_territoire',
        'superficie_ha',
        'role_gestionnaire_membres',
        'is_active',
        'date_creation',
    )
    list_filter = ('type_territoire', 'is_active', 'role_gestionnaire_membres')
    search_fields = ('nom', 'slug', 'description')
    prepopulated_fields = {'slug': ('nom',)}
    readonly_fields = ('id', 'superficie_ha', 'date_creation', 'date_modification')
    inlines = [DossierMembershipInline, ZoneSecteurInline]
    fieldsets = (
        ('Identité du Dossier', {
            'fields': ('id', 'nom', 'slug', 'description', 'type_territoire', 'is_active')
        }),
        ('Paramétrage SIG & Carte', {
            'fields': ('geometrie', 'centre_carte', 'zoom_defaut', 'srid_metrique', 'superficie_ha')
        }),
        ('Modules & Gouvernance', {
            'fields': ('modules_config', 'role_gestionnaire_membres')
        }),
        ('Traçabilité Temporelle', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DossierMembership)
class DossierMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'dossier', 'role', 'assigned_by', 'date_creation')
    list_filter = ('role', 'dossier')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'dossier__nom')
    readonly_fields = ('id', 'date_creation', 'date_modification')
    autocomplete_fields = ('user', 'dossier', 'assigned_by')


@admin.register(ZoneSecteur)
class ZoneSecteurAdmin(admin.GISModelAdmin):
    list_display = ('nom', 'code', 'dossier', 'type_zone', 'superficie_ha', 'statut')
    list_filter = ('dossier', 'type_zone', 'statut')
    search_fields = ('nom', 'code', 'responsable_nom', 'dossier__nom')
    readonly_fields = ('superficie_m2', 'superficie_ha', 'date_creation', 'date_modification')
    autocomplete_fields = ('dossier',)


@admin.register(UniteBatie)
class UniteBatieAdmin(admin.GISModelAdmin):
    list_display = ('code', 'nom', 'dossier', 'zone_secteur', 'type_bati', 'statut_occupation', 'superficie_m2', 'est_actif')
    list_filter = ('dossier', 'type_bati', 'statut_occupation', 'est_actif')
    search_fields = ('code', 'nom', 'dossier__nom', 'zone_secteur__nom')
    readonly_fields = ('superficie_m2', 'superficie_ha', 'date_creation', 'date_modification')
    autocomplete_fields = ('dossier', 'zone_secteur')


@admin.register(ReseauLineaire)
class ReseauLineaireAdmin(admin.GISModelAdmin):
    list_display = ('code', 'nom', 'dossier', 'type_voie', 'longueur_metres', 'etat_chaussee')
    list_filter = ('dossier', 'type_voie')
    search_fields = ('code', 'nom', 'dossier__nom')
    readonly_fields = ('longueur_metres', 'date_creation', 'date_modification')
    autocomplete_fields = ('dossier',)


@admin.register(SignalementDommage)
class SignalementDommageAdmin(admin.GISModelAdmin):
    list_display = ('numero', 'titre', 'dossier', 'zone_secteur', 'categorie', 'priorite', 'statut', 'date_signalement')
    list_filter = ('dossier', 'categorie', 'priorite', 'statut')
    search_fields = ('numero', 'titre', 'description', 'dossier__nom')
    readonly_fields = ('numero', 'date_signalement', 'date_creation', 'date_modification')
    autocomplete_fields = ('dossier', 'zone_secteur', 'auteur')


