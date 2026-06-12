from django.urls import path
from . import views

app_name = 'foncier'

urlpatterns = [
    path('cartographie/', views.cartographie, name='cartographie'),
    path('espaces/', views.espaces_list, name='espaces'),
    path('espaces/ajouter/', views.espace_create, name='espace_create'),
    path('espaces/<int:pk>/modifier/', views.espace_update, name='espace_update'),
    path('espaces/<int:pk>/supprimer/', views.espace_delete, name='espace_delete'),
    path('batiments/', views.batiments_list, name='batiments'),
    path('batiments/<int:pk>/', views.batiment_detail, name='batiment_detail'),
    path('batiments/ajouter/', views.batiment_create, name='batiment_create'),
    path('batiments/<int:pk>/modifier/', views.batiment_update, name='batiment_update'),
    path('batiments/<int:pk>/supprimer/', views.batiment_delete, name='batiment_delete'),
]
