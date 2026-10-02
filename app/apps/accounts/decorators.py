from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def require_permission(perm_code: str):
    """
    Niveau 1 de défense en profondeur (Garantie Ultime Backend) :
    Vérifie que l'utilisateur connecté détient la permission atomique [domaine]:[action].
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not request.user.has_perm_code(perm_code):
                messages.error(request, f"Accès refusé. Habilitation manquante : {perm_code}")
                # Redirection vers la galerie de dossiers ou page d'accueil
                return redirect('dossiers:list')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def superuser_required(view_func):
    """
    Contrôle d'accès strict réservé au Superuser racine de la plateforme.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_superuser or request.user.role == 'superuser'):
            messages.error(request, "Accès strictement réservé au Super Administrateur.")
            return redirect('dossiers:list')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, "Accès refusé. Droits d'administrateur requis.")
            return redirect('dossiers:list')
        return view_func(request, *args, **kwargs)
    return wrapper


def foncier_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.can_manage_foncier:
            messages.error(request, "Accès refusé. Droits de gestion foncière requis.")
            return redirect('dossiers:list')
        return view_func(request, *args, **kwargs)
    return wrapper


def domaine_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_domaine_foncier:
            messages.error(request, "Accès refusé.")
            return redirect('dossiers:list')
        return view_func(request, *args, **kwargs)
    return wrapper

