from django.urls import path
from . import views

app_name = 'drones'

urlpatterns = [
    path('', views.missions_list, name='missions'),
    path('ajouter/', views.mission_create, name='mission_create'),
    path('<int:pk>/modifier/', views.mission_update, name='mission_update'),
    path('<int:pk>/supprimer/', views.mission_delete, name='mission_delete'),
    path('<int:mission_pk>/orthophoto/ajouter/', views.orthophoto_add, name='orthophoto_add'),
    path('orthophoto/<int:pk>/supprimer/', views.orthophoto_delete, name='orthophoto_delete'),
]
