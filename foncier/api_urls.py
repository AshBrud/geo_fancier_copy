from django.urls import path
from . import api_views

urlpatterns = [
    path('espaces/', api_views.EspaceAPIView.as_view(), name='api_espaces'),
    path('batiments/', api_views.BatimentAPIView.as_view(), name='api_batiments'),
    path('stats/', api_views.StatsAPIView.as_view(), name='api_stats'),
    path('orthophotos/', api_views.OrthophotoAPIView.as_view(), name='api_orthophotos'),
    path('terrains/', api_views.TerrainAPIView.as_view(), name='api_terrains'),
    path('espaces-verts/', api_views.EspaceVertAPIView.as_view(), name='api_espaces_verts'),
    path('voiries/', api_views.VoirieAPIView.as_view(), name='api_voiries'),
    path('points-interet/', api_views.PointInteretAPIView.as_view(), name='api_points_interet'),
]
