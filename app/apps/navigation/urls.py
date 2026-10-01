from django.urls import path
from . import views

app_name = 'navigation'

urlpatterns = [
    path('', views.recherche, name='recherche'),
    path('ajax/', views.recherche_ajax, name='recherche_ajax'),
]
