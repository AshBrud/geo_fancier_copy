import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.models import CustomUser, ActivityLog, Role
from accounts.forms import AdminCreationForm, StandardUserCreationForm, UserUpdateForm
from accounts.decorators import admin_required, require_permission
from accounts.services.services_rbac import create_managed_user, soft_delete_user, can_manage_target_user


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
        'nb_admins': CustomUser.objects.filter(role__in=[CustomUser.ROLE_ADMIN, 'admin']).count(),
        'nb_recents': CustomUser.objects.filter(last_login__gte=seuil_recent).count(),
        'is_super': request.user.is_superuser or request.user.role == 'superuser',
    }
    return render(request, 'accounts/management/list.html', context)


@login_required
@require_permission('users:create')
def user_create(request):
    is_super = request.user.is_superuser or request.user.role == 'superuser'
    target_role = request.GET.get('role', 'standard')

    if is_super and target_role == 'admin':
        form = AdminCreationForm(request.POST or None)
    else:
        form = StandardUserCreationForm(request.POST or None, operator=request.user)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        role_to_assign = 'admin' if (is_super and target_role == 'admin') else 'standard'
        try:
            user = create_managed_user(
                operator=request.user,
                username=cd['username'],
                email=cd['email'],
                password=cd['password'],
                role_code=role_to_assign,
                first_name=cd.get('first_name', ''),
                last_name=cd.get('last_name', ''),
                telephone=cd.get('telephone', ''),
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f"Compte '{user.username}' créé avec succès [{user.get_role_display()}].")
            return redirect('accounts:users')
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {e}")

    return render(request, 'accounts/management/form.html', {
        'form': form,
        'action': 'Créer',
        'target_role': target_role,
        'is_super': is_super
    })


@login_required
@require_permission('users:update')
def user_update(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)

    allowed, msg = can_manage_target_user(request.user, user)
    if not allowed and request.user.id != user.id:
        messages.error(request, msg)
        return redirect('accounts:users')

    form = UserUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=user,
        operator=request.user
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.objects.create(
            user=request.user,
            action="MODIFICATION_UTILISATEUR",
            detail=f"Modification des attributs du compte '{user.username}'.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Utilisateur '{user.username}' mis à jour avec succès.")
        return redirect('accounts:users')

    return render(request, 'accounts/management/form.html', {'form': form, 'action': 'Modifier', 'obj': user})


@login_required
@require_permission('users:deactivate')
def user_delete(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)

    allowed, message = can_manage_target_user(request.user, target_user)
    if not allowed:
        messages.error(request, f"Action interdite : {message}")
        return redirect('accounts:users')

    if request.method == 'POST':
        try:
            soft_delete_user(
                operator=request.user,
                target_user=target_user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Le compte de l'utilisateur '{target_user.username}' a été désactivé avec succès (Soft-Delete).")
            return redirect('accounts:users')
        except Exception as e:
            messages.error(request, f"Erreur lors de la désactivation : {e}")
            return redirect('accounts:users')

    return render(request, 'accounts/management/confirm_delete.html', {'obj': target_user})


@login_required
@require_permission('audit:view')
def activity_log(request):
    logs = ActivityLog.objects.select_related('user').all()[:200]
    return render(request, 'accounts/management/activity_log.html', {'logs': logs})

