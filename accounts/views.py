from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import CustomUser, ActivityLog
from .forms import LoginForm, RegisterForm, UserUpdateForm, ProfileForm
from .decorators import admin_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        ActivityLog.objects.create(
            user=user, action='Connexion',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return redirect('dashboard:index')
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
        return redirect('dashboard:index')
    return render(request, 'accounts/register.html', {'form': form})


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
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'accounts/users_list.html', {'users': users})


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
