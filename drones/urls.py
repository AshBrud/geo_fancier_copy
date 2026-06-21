from django.urls import path
from . import views

app_name = 'drones'

urlpatterns = [
    path('', views.orthophotos_list, name='missions'),
    path('importer/', views.import_orthophoto, name='import_orthophoto'),
    path('orthophoto/<int:pk>/supprimer/', views.orthophoto_delete, name='orthophoto_delete'),
]
