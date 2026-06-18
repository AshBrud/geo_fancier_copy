from django.urls import path
from . import views

app_name = 'drones'

urlpatterns = [
    path('', views.missions_list, name='missions'),
    path('ajouter/', views.mission_create, name='mission_create'),
    path('<int:pk>/', views.mission_detail, name='mission_detail'),
    path('<int:pk>/modifier/', views.mission_update, name='mission_update'),
    path('<int:pk>/supprimer/', views.mission_delete, name='mission_delete'),
    # Import orthophoto — global ou rattaché à une mission
    path('import-orthophoto/', views.import_orthophoto, name='import_orthophoto'),
    path('<int:mission_pk>/import-orthophoto/', views.import_orthophoto, name='import_orthophoto_mission'),
    # Suppression orthophoto
    path('orthophoto/<int:pk>/supprimer/', views.orthophoto_delete, name='orthophoto_delete'),
]
