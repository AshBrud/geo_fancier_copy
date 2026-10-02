from django.urls import path
from . import views

app_name = 'dossiers'

urlpatterns = [
    # Galerie principale / sélecteur
    path('', views.dossier_list, name='list'),
    path('switch-clear/', views.dossier_switch_clear, name='switch_clear'),

    # Actions contextuelles
    path('<slug:slug>/select/', views.dossier_select, name='select'),
    path('<slug:slug>/members/', views.dossier_members, name='members'),
    path('<slug:slug>/members/assign/', views.dossier_assign_member, name='assign_member'),
    path('<slug:slug>/members/<int:user_id>/revoke/', views.dossier_revoke_member, name='revoke_member'),
]
