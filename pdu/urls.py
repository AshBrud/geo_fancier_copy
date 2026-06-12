from django.urls import path
from . import views

app_name = 'pdu'

urlpatterns = [
    path('', views.aide_pdu, name='aide_pdu'),
    path('statistiques/', views.statistiques, name='statistiques'),
]
