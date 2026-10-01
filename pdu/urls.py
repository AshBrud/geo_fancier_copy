from django.urls import path
from . import views

app_name = 'pdu'

urlpatterns = [
    path('', views.statistiques, name='statistiques'),
]
