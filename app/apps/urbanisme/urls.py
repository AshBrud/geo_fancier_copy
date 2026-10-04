from django.urls import path
from . import views

app_name = 'urbanisme'

urlpatterns = [
    # ── Projets de Construction & Planification Urbaine ───────────────────────
    path('', views.constructions_list, name='index'),
    path('constructions/', views.constructions_list, name='constructions'),
    path('liste/', views.constructions_list, name='list'),  # Alias rétrocompatible
    path('<int:pk>/statut/', views.construction_update_statut, name='update_statut'),
    path('<int:pk>/supprimer/', views.construction_delete, name='delete'),

    # ── Études de Faisabilité & Moteur de Recommandation IA ───────────────────
    path('faisabilite/', views.nouvelle_construction, name='faisabilite'),
    path('nouvelle/', views.nouvelle_construction, name='nouvelle'),  # Alias rétrocompatible
    path('recommander/', views.recommander_emplacements_view, name='recommander'),

    # ── Historique des Chantiers & Interventions ──────────────────────────────
    path('historique/', views.historique_list, name='historique'),
    path('historique/ajouter/', views.historique_create, name='historique_create'),
    path('historique/<int:pk>/supprimer/', views.historique_delete, name='historique_delete'),
]
