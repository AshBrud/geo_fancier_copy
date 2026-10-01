from django.urls import path
from . import views

app_name = 'constructions'

urlpatterns = [
    path('nouvelle/', views.nouvelle_construction, name='nouvelle'),
    path('recommander/', views.recommander_emplacements_view, name='recommander'),
    path('liste/', views.constructions_list, name='list'),
    path('<int:pk>/statut/', views.construction_update_statut, name='update_statut'),
    path('<int:pk>/supprimer/', views.construction_delete, name='delete'),
    path('historique/', views.historique_list, name='historique'),
    path('historique/ajouter/', views.historique_create, name='historique_create'),
    path('historique/<int:pk>/supprimer/', views.historique_delete, name='historique_delete'),
]
