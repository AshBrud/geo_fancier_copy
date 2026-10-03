from django.urls import path
from . import views

app_name = 'urbanisme'

urlpatterns = [
    path('', views.constructions_list, name='index'),
    path('nouvelle/', views.nouvelle_construction, name='nouvelle'),
    path('faisabilite/', views.nouvelle_construction, name='faisabilite'),
    path('recommander/', views.recommander_emplacements_view, name='recommander'),
    path('liste/', views.constructions_list, name='list'),
    path('constructions/', views.constructions_list, name='constructions'),
    path('<int:pk>/statut/', views.construction_update_statut, name='update_statut'),
    path('<int:pk>/supprimer/', views.construction_delete, name='delete'),
    path('historique/', views.historique_list, name='historique'),
    path('historique/ajouter/', views.historique_create, name='historique_create'),
    path('historique/<int:pk>/supprimer/', views.historique_delete, name='historique_delete'),
]
