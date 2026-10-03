from django.urls import path
from . import views

app_name = 'territoire'

urlpatterns = [
    path('', views.cartographie, name='index'),
    path('cartographie/', views.cartographie, name='cartographie'),
    path('carte/', views.cartographie, name='carte'),
    path('espaces/', views.espaces_list, name='espaces'),
    path('espaces/campus/', views.campus_detail, name='campus_detail'),
    path('espaces/ajouter/', views.espace_create, name='espace_create'),
    path('espaces/<int:pk>/', views.espace_detail, name='espace_detail'),
    path('espaces/<int:pk>/modifier/', views.espace_update, name='espace_update'),
    path('espaces/<int:pk>/supprimer/', views.espace_delete, name='espace_delete'),
    path('batiments/', views.batiments_list, name='batiments'),
    path('batiments/<int:pk>/', views.batiment_detail, name='batiment_detail'),
    path('batiments/ajouter/', views.batiment_create, name='batiment_create'),
    path('batiments/importer-sig/', views.batiment_import_sig, name='batiment_import_sig'),
    path('batiments/<int:pk>/modifier/', views.batiment_update, name='batiment_update'),
    path('batiments/<int:pk>/supprimer/', views.batiment_delete, name='batiment_delete'),
    path('suivi-travaux/', views.suivi_travaux_list, name='suivi_travaux'),
    path('suivi-travaux/<int:pk>/modifier/', views.suivi_travaux_update, name='suivi_travaux_update'),

    path('terrains/', views.terrains_list, name='terrains'),
    path('parcelles/', views.terrains_list, name='parcelles'),
    path('terrains/ajouter/', views.terrain_create, name='terrain_create'),
    path('terrains/<int:pk>/', views.terrain_detail, name='terrain_detail'),
    path('terrains/<int:pk>/modifier/', views.terrain_update, name='terrain_update'),
    path('terrains/<int:pk>/supprimer/', views.terrain_delete, name='terrain_delete'),

    path('espaces-verts/', views.espaces_verts_list, name='espaces_verts'),
    path('espaces-verts/ajouter/', views.espace_vert_create, name='espace_vert_create'),
    path('espaces-verts/<int:pk>/', views.espace_vert_detail, name='espace_vert_detail'),
    path('espaces-verts/<int:pk>/modifier/', views.espace_vert_update, name='espace_vert_update'),
    path('espaces-verts/<int:pk>/supprimer/', views.espace_vert_delete, name='espace_vert_delete'),

    path('voiries/', views.voiries_list, name='voiries'),
    path('voirie/', views.voiries_list, name='voirie'),
    path('voiries/ajouter/', views.voirie_create, name='voirie_create'),
    path('voiries/<int:pk>/', views.voirie_detail, name='voirie_detail'),
    path('voiries/<int:pk>/modifier/', views.voirie_update, name='voirie_update'),
    path('voiries/<int:pk>/supprimer/', views.voirie_delete, name='voirie_delete'),
]
