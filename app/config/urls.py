from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from django.http import JsonResponse
from django.db import connection

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
        return JsonResponse({"status": "ok", "database": "connected"}, status=200)
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=503)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('foncier/', include('foncier.urls')),
    path('drones/', include('drones.urls')),
    path('constructions/', include('constructions.urls')),
    path('navigation/', include('navigation.urls')),
    path('pdu/', include('pdu.urls')),
    path('commune/', include('commune.urls')),
    path('api/', include('foncier.api_urls')),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
