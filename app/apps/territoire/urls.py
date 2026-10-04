from django.urls import path
from . import views

app_name = 'territoire'

urlpatterns = [
    # ── Cartographie SIG ──────────────────────────────────────────────────────
    path('', views.cartographie, name='index'),
    path('carte/', views.cartographie, name='carte'),
    path('cartographie/', views.cartographie, name='cartographie'),

    # ── Subdivisions Spatiales (ZoneSecteur : Villages, Quartiers, Secteurs) ───
    path('zones/', views.zones_secteurs_list, name='zones'),
    path('zones/ajouter/', views.zone_secteur_create, name='zone_create'),
    path('zones/<int:pk>/', views.zone_secteur_detail, name='zone_detail'),
    path('zones/<int:pk>/modifier/', views.zone_secteur_update, name='zone_update'),
    path('zones/<int:pk>/supprimer/', views.zone_secteur_delete, name='zone_delete'),

    # ── Recensement Bâti (UniteBatie : Concessions, Maisons, Bâtiments) ────────
    path('batiments/', views.unites_baties_list, name='batiments'),
    path('batiments/ajouter/', views.unite_batie_create, name='batiment_create'),
    path('batiments/importer-sig/', views.unite_batie_import_sig, name='batiment_import_sig'),
    path('batiments/<int:pk>/', views.unite_batie_detail, name='batiment_detail'),
    path('batiments/<int:pk>/modifier/', views.unite_batie_update, name='batiment_update'),
    path('batiments/<int:pk>/supprimer/', views.unite_batie_delete, name='batiment_delete'),

    # ── Réseaux Linéaires (ReseauLineaire : Pistes, Routes, Voiries, Allées) ───
    path('reseaux/', views.reseaux_lineaires_list, name='reseaux'),
    path('reseaux/ajouter/', views.reseau_lineaire_create, name='reseau_create'),
    path('reseaux/<int:pk>/', views.reseau_lineaire_detail, name='reseau_detail'),
    path('reseaux/<int:pk>/modifier/', views.reseau_lineaire_update, name='reseau_update'),
    path('reseaux/<int:pk>/supprimer/', views.reseau_lineaire_delete, name='reseau_delete'),

    # ── Suivi de Travaux & Chantiers ──────────────────────────────────────────
    path('suivi-travaux/', views.suivi_travaux_list, name='suivi_travaux'),
    path('suivi-travaux/<int:pk>/modifier/', views.suivi_travaux_update, name='suivi_travaux_update'),
]
