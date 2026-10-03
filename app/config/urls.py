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
    path('dossiers/', include('dossiers.urls')),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('territoire/', include('territoire.urls')),
    path('drones/', include('drones.urls')),
    path('urbanisme/', include('urbanisme.urls')),
    path('navigation/', include('navigation.urls')),
    path('pdu/', include('pdu.urls')),
    path('habitations/', include('habitations.urls')),
    path('api/', include('territoire.api_urls')),
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('register/', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('', RedirectView.as_view(url='/dossiers/', permanent=False)),

    # =========================================================================
    # ESPACE DE TRAVAIL TERRITORIAL V2 (Dossier-First Routing: /{slug}/...)
    # =========================================================================
    path('<slug:dossier_slug>/', include('dossiers.workspace_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
