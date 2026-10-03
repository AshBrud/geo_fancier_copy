from django.urls import path
from . import views

app_name = 'dossiers'

urlpatterns = [
    # Galerie principale / sélecteur
    path('', views.dossier_list, name='list'),
    path('create/', views.dossier_create, name='create'),
    path('switch-clear/', views.dossier_switch_clear, name='switch_clear'),

    # Actions contextuelles
    path('<slug:slug>/select/', views.dossier_select, name='select'),
]
