from django.urls import path
from . import views

app_name = 'drones'

urlpatterns = [
    path('', views.orthophotos_list, name='missions'),
    path('importer/', views.import_orthophoto, name='import_orthophoto'),
    path('orthophoto/<int:pk>/supprimer/', views.orthophoto_delete, name='orthophoto_delete'),
    # Enregistrement flux live
    path('flux/start/', views.flux_start, name='flux_start'),
    path('flux/stop/', views.flux_stop, name='flux_stop'),
    path('flux/videos/', views.flux_videos_list, name='flux_videos'),
    path('flux/videos/<int:pk>/supprimer/', views.flux_video_delete, name='flux_video_delete'),
    # Photos drone
    path('flux/capturer/', views.capture_photo, name='capture_photo'),
    path('photos/', views.photos_drone_list, name='photos_drone'),
    path('photos/<int:pk>/supprimer/', views.photo_drone_delete, name='photo_drone_delete'),
]
