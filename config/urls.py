from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('foncier/', include('foncier.urls')),
    path('drones/', include('drones.urls')),
    path('constructions/', include('constructions.urls')),
    path('navigation/', include('navigation.urls')),
    path('pdu/', include('pdu.urls')),
    path('api/', include('foncier.api_urls')),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
