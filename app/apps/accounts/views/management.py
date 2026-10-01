import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.models import CustomUser, ActivityLog
from accounts.forms import RegisterForm, UserUpdateForm
from accounts.decorators import admin_required


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
    return render(request, 'accounts/management/list.html', context)


@login_required
@admin_required
def user_create(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Utilisateur {user.username} créé.')
        return redirect('accounts:users')
    return render(request, 'accounts/management/form.html', {'form': form, 'action': 'Créer'})


@login_required
@admin_required
def user_update(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    form = UserUpdateForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Utilisateur {user.username} mis à jour.')
        return redirect('accounts:users')
    return render(request, 'accounts/management/form.html', {'form': form, 'action': 'Modifier', 'obj': user})


@login_required
@admin_required
def user_delete(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Utilisateur {username} supprimé.')
        return redirect('accounts:users')
    return render(request, 'accounts/management/confirm_delete.html', {'obj': user})


@login_required
@admin_required
def activity_log(request):
    logs = ActivityLog.objects.select_related('user').all()[:200]
    return render(request, 'accounts/management/activity_log.html', {'logs': logs})
