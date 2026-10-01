from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def _exiger(test, message):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or not test(request.user):
                messages.error(request, message)
                return redirect('commune:carte')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


commune_view_required = _exiger(
    lambda u: u.can_view_commune, "Accès réservé aux responsables communaux et fonciers.")
commune_edit_required = _exiger(
    lambda u: u.can_edit_commune, "Seul un administrateur peut modifier les données cartographiques.")
signalements_required = _exiger(
    lambda u: u.can_manage_signalements, "Accès réservé au responsable communal.")
