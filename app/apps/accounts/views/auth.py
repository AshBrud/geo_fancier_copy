from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import ActivityLog
from accounts.forms import LoginForm, RegisterForm


def _suivant(request):
    """URL de retour (?next=) si elle pointe bien vers la plateforme."""
    nxt = request.POST.get('next') or request.GET.get('next') or ''
    if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                       require_https=request.is_secure()):
        return nxt
    return ''


def _contexte_commune():
    """Identité de la commune et villages affichés dans le défilement des pages d'accès."""
    from commune.models import Commune, Village
    return {
        'commune': Commune.objects.first(),
        'villages_defilement': Village.objects.order_by('nom').only('nom', 'code'),
    }


def login_view(request):
    # Pas de redirection automatique quand une session est déjà ouverte : sur un
    # ordinateur partagé, chacun doit pouvoir se connecter avec son propre compte
    # (la nouvelle connexion remplace alors la session précédente).
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        precedent = request.user if request.user.is_authenticated else None
        if precedent and precedent.pk != user.pk:
            ActivityLog.objects.create(
                user=precedent, action='Déconnexion (changement de compte)',
                ip_address=request.META.get('REMOTE_ADDR')
            )
        login(request, user)
        ActivityLog.objects.create(
            user=user, action='Connexion',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return redirect(_suivant(request) or 'dashboard:index')
    from foncier.models import Espace, Batiment
    from drones.models import Orthophoto
    return render(request, 'accounts/auth/login.html', {
        'form': form,
        'nb_espaces': Espace.objects.count(),
        'nb_batiments': Batiment.objects.count(),
        'nb_orthophotos': Orthophoto.objects.count(),
        'next': _suivant(request),
        'page_auth': True,
        **_contexte_commune(),
    })


def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
        return redirect('dashboard:index')
    return render(request, 'accounts/auth/register.html', {'form': form, 'page_auth': True, **_contexte_commune()})


@login_required
def logout_view(request):
    if request.method == 'POST':
        ActivityLog.objects.create(
            user=request.user, action='Déconnexion',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        logout(request)
        return redirect('accounts:login')
    return redirect('dashboard:index')
