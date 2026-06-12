from django.urls import path
from . import api_views

urlpatterns = [
    path('espaces/', api_views.EspaceAPIView.as_view(), name='api_espaces'),
    path('batiments/', api_views.BatimentAPIView.as_view(), name='api_batiments'),
    path('stats/', api_views.StatsAPIView.as_view(), name='api_stats'),
]
