from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_router, name='index'),
    path('<slug:slug>/', views.dossier_dashboard, name='dossier_dashboard'),
]
