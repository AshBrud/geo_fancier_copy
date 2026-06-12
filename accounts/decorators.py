from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, "Accès refusé. Droits d'administrateur requis.")
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def foncier_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.can_manage_foncier:
            messages.error(request, "Accès refusé. Droits de gestion foncière requis.")
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def domaine_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_domaine_foncier:
            messages.error(request, "Accès refusé.")
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper
