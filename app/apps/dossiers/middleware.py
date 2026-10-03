from django.shortcuts import redirect
from django.contrib import messages
from dossiers.selectors import (
    get_dossier_by_slug, 
    get_accessible_dossiers_for_user, 
    get_dossier_by_id
)


class ActiveDossierMiddleware:
    """
    Middleware d'isolation et d'orchestration de l'espace de travail V2 (Dossier-First).

    Intercepte le paramètre `dossier_slug` présent dans les URLs /{slug}/... :
      1. Résout l'instance Dossier correspondante.
      2. Valide l'éligibilité d'accès de l'utilisateur connecté.
      3. Injecte `request.active_dossier` et synchronise la session.
      4. Nettoie `view_kwargs` pour que les vues descendantes reçoivent exactement leurs paramètres prévus.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        dossier_slug = view_kwargs.pop('dossier_slug', None)

        if not dossier_slug:
            # Si pas de slug dans l'URL, vérifier si un dossier est mémorisé en session
            active_dossier_id = request.session.get('active_dossier_id')
            if active_dossier_id and not hasattr(request, 'active_dossier'):
                request.active_dossier = get_dossier_by_id(active_dossier_id)
            return None

        # Résolution par slug
        dossier = get_dossier_by_slug(dossier_slug)
        if not dossier:
            messages.error(request, f"Le dossier territorial « {dossier_slug} » est introuvable.")
            return redirect('dossiers:list')

        # Contrôle d'accès si l'utilisateur est authentifié
        if request.user.is_authenticated and not request.user.is_superuser:
            accessible = get_accessible_dossiers_for_user(request.user)
            if not accessible.filter(id=dossier.id).exists():
                messages.error(request, f"Vous n'avez pas l'habilitation requise pour accéder au dossier « {dossier.nom} ».")
                return redirect('dossiers:list')

        # Attachement contextuel
        request.active_dossier = dossier
        request.session['active_dossier_id'] = str(dossier.id)
        request.session['active_dossier_slug'] = dossier.slug

        return None
