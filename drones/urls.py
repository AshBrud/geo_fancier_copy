from django.urls import path
from . import views

app_name = 'drones'

urlpatterns = [
    # Hub
    path('', views.mission_list, name='missions'),

    # Missions CRUD
    path('missions/nouvelle/', views.mission_create, name='mission_create'),
    path('missions/<int:pk>/', views.mission_detail, name='mission_detail'),
    path('missions/<int:pk>/modifier/', views.mission_update, name='mission_update'),
    path('missions/<int:pk>/supprimer/', views.mission_delete, name='mission_delete'),
    path('missions/<int:pk>/traitement/', views.mission_marquer_traitement, name='mission_marquer_traitement'),

    # Photos (import multi-fichiers rattaché à une mission)
    path('missions/<int:pk>/photos/importer/', views.mission_photos_import, name='mission_photos_import'),

    # Orthophotos (autonome ou rattachée à une mission)
    path('importer/', views.import_orthophoto, name='import_orthophoto'),
    path('missions/<int:pk>/orthophoto/importer/', views.import_orthophoto, name='mission_orthophoto_import'),
    path('orthophoto/<int:pk>/supprimer/', views.orthophoto_delete, name='orthophoto_delete'),
    path('orthophoto/<int:pk>/valider/', views.orthophoto_validate, name='orthophoto_validate'),
    path('orthophoto/<int:pk>/integrer/', views.orthophoto_integrate, name='orthophoto_integrate'),

    # Perspectives (flux live drone relocalisé + photos ad-hoc)
    path('perspectives/', views.perspectives, name='perspectives'),
    path('flux/start/', views.flux_start, name='flux_start'),
    path('flux/stop/', views.flux_stop, name='flux_stop'),
    path('flux/videos/', views.flux_videos_list, name='flux_videos'),
    path('flux/videos/<int:pk>/supprimer/', views.flux_video_delete, name='flux_video_delete'),
    path('flux/capturer/', views.capture_photo, name='capture_photo'),
    path('photos/', views.photos_drone_list, name='photos_drone'),
    path('photos/<int:pk>/supprimer/', views.photo_drone_delete, name='photo_drone_delete'),
]
