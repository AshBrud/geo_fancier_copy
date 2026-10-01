from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('universite/', views.universite, name='universite'),
    path('home/', views.home, name='home'),
]
