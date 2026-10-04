from django.urls import path
from . import api_views

urlpatterns = [
    # ── Routes Canoniques V2 ──────────────────────────────────────────────────
    path('zones/', api_views.ZoneSecteurAPIView.as_view(), name='api_zones'),
    path('batiments/', api_views.UniteBatieAPIView.as_view(), name='api_batiments'),
    path('reseaux/', api_views.ReseauLineaireAPIView.as_view(), name='api_reseaux'),
    path('stats/', api_views.StatsAPIView.as_view(), name='api_stats'),
    path('orthophotos/', api_views.OrthophotoAPIView.as_view(), name='api_orthophotos'),
]
