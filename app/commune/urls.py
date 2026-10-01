from django.urls import path

from . import views

app_name = 'commune'

urlpatterns = [
    # Carte — cœur du système
    path('', views.carte, name='carte'),
    path('limite/', views.commune_edit, name='commune_edit'),
    path('api/villages/<int:pk>/maisons/', views.api_village_maisons, name='api_village_maisons'),

    path('villages/', views.villages_list, name='villages'),
    path('villages/ajouter/', views.village_create, name='village_create'),
    path('villages/<int:pk>/', views.village_detail, name='village_detail'),
    path('villages/<int:pk>/modifier/', views.village_update, name='village_update'),
    path('villages/<int:pk>/supprimer/', views.village_delete, name='village_delete'),

    path('maisons/', views.maisons_list, name='maisons'),
    path('maisons/ajouter/', views.maison_create, name='maison_create'),
    path('maisons/<int:pk>/modifier/', views.maison_update, name='maison_update'),
    path('maisons/<int:pk>/supprimer/', views.maison_delete, name='maison_delete'),

    path('pistes/', views.pistes_list, name='pistes'),
    path('pistes/ajouter/', views.piste_create, name='piste_create'),
    path('pistes/<int:pk>/modifier/', views.piste_update, name='piste_update'),
    path('pistes/<int:pk>/supprimer/', views.piste_delete, name='piste_delete'),

    # Signalements
    path('signalements/', views.signalements, name='signalements'),
    path('signalements/nouveau/', views.signalement_create, name='signalement_create'),
    path('signalements/<int:pk>/', views.signalement_detail, name='signalement_detail'),

    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/', views.notification_ouvrir, name='notification_ouvrir'),
]
