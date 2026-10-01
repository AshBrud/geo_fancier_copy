from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
import datetime
from .models import CustomUser, ActivityLog
from .forms import LoginForm, RegisterForm, UserUpdateForm, ProfileForm
from .decorators import admin_required


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
    return render(request, 'accounts/login.html', {
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
    return render(request, 'accounts/register.html', {'form': form, 'page_auth': True, **_contexte_commune()})


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


@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
@admin_required
def users_list(request):
    qs = CustomUser.objects.all()
    q = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    statut_filter = request.GET.get('statut', '')

    if q:
        qs = qs.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    if role_filter:
        qs = qs.filter(role=role_filter)
    if statut_filter == 'actif':
        qs = qs.filter(is_active=True)
    elif statut_filter == 'inactif':
        qs = qs.filter(is_active=False)

    qs = qs.order_by('-date_joined')
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    seuil_recent = timezone.now() - datetime.timedelta(days=30)
    context = {
        'page_obj': page,
        'q': q, 'role_filter': role_filter, 'statut_filter': statut_filter,
        'roles': CustomUser.ROLES,
        'total_users': CustomUser.objects.count(),
        'nb_actifs': CustomUser.objects.filter(is_active=True).count(),
        'nb_admins': CustomUser.objects.filter(role=CustomUser.ROLE_ADMIN).count(),
        'nb_recents': CustomUser.objects.filter(last_login__gte=seuil_recent).count(),
    }
    return render(request, 'accounts/users_list.html', context)


@login_required
@admin_required
def user_create(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Utilisateur {user.username} créé.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_form.html', {'form': form, 'action': 'Créer'})


@login_required
@admin_required
def user_update(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    form = UserUpdateForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Utilisateur {user.username} mis à jour.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_form.html', {'form': form, 'action': 'Modifier', 'obj': user})


@login_required
@admin_required
def user_delete(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Utilisateur {username} supprimé.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_confirm_delete.html', {'obj': user})


@login_required
@admin_required
def activity_log(request):
    logs = ActivityLog.objects.select_related('user').all()[:200]
    return render(request, 'accounts/activity_log.html', {'logs': logs})
