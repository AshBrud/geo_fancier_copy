from django.urls import path, include
from django.views.generic import RedirectView
from dashboard import views as dashboard_views
from dossiers import views as dossier_views

app_name = 'workspace'

urlpatterns = [
    # Redirection par défaut vers le dashboard du territoire
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),
    path('dashboard/', dashboard_views.dossier_dashboard, name='dashboard'),

    # Modules métier de l'espace de travail
    path('urbanisme/', include('urbanisme.urls')),
    path('territoire/', include('territoire.urls')),
    path('habitations/', include('habitations.urls')),
    path('drones/', include('drones.urls')),
    path('pdu/', include('pdu.urls')),

    # Gestion de l'équipe et des membres du dossier
    path('membres/', dossier_views.dossier_members, name='members'),
    path('membres/assign/', dossier_views.dossier_assign_member, name='assign_member'),
    path('membres/<int:user_id>/revoke/', dossier_views.dossier_revoke_member, name='revoke_member'),

    # Configuration des modules & Préférences du dossier
    path('parametres/', dossier_views.dossier_settings, name='settings'),
]
