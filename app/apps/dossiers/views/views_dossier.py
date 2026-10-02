from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dossiers.selectors import (
    get_accessible_dossiers_for_user,
    get_all_dossiers,
    get_dossier_by_slug,
    get_dossier_members,
    get_user_membership,
)
from dossiers.services import (
    assign_user_to_dossier,
    configure_dossier_modules,
    create_dossier,
    delegate_dossier_role,
    revoke_user_from_dossier,
)

User = get_user_model()


@login_required
def dossier_list(request):
    """
    Galerie principale des dossiers territoriaux (Écran d'accueil post-connexion).
    - Superuser : voit l'ensemble exhaustif des dossiers et les outils de gouvernance.
    - Admin / Standard : voit les dossiers auxquels il a été formellement affecté.
    """
    dossiers = get_accessible_dossiers_for_user(request.user)

    context = {
        'dossiers': dossiers,
        'total_dossiers_count': dossiers.count(),
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'dossiers/list.html', context)


@login_required
def dossier_select(request, slug):
    """
    Sélectionne un dossier comme espace de travail actif,
    mémorise le choix en session utilisateur et redirige vers le dashboard.
    """
    dossier = get_object_or_404(get_accessible_dossiers_for_user(request.user), slug=slug)

    request.session['active_dossier_id'] = str(dossier.id)
    request.session['active_dossier_slug'] = dossier.slug
    messages.success(request, f"Espace de travail « {dossier.nom} » activé.")

    return redirect('dashboard:dossier_dashboard', slug=dossier.slug)


@login_required
def dossier_switch_clear(request):
    """
    Désélectionne le dossier actif en session pour revenir à la Galerie générale.
    """
    request.session.pop('active_dossier_id', None)
    request.session.pop('active_dossier_slug', None)
    messages.info(request, "Retour à la sélection des territoires.")
    return redirect('dossiers:list')


@login_required
def dossier_members(request, slug):
    """
    Gestion des membres d'un dossier territorial.
    Accessible par le Superuser ou par l'Admin délégué sur ce dossier.
    """
    dossier = get_object_or_404(get_accessible_dossiers_for_user(request.user), slug=slug)

    if not dossier.can_user_manage_members(request.user):
        raise PermissionDenied("Vous n'êtes pas habilité à gérer les membres de ce dossier.")

    memberships = get_dossier_members(dossier)
    existing_user_ids = memberships.values_list('user_id', flat=True)
    available_users = User.objects.filter(is_active=True).exclude(id__in=existing_user_ids).order_by('username')

    context = {
        'dossier': dossier,
        'memberships': memberships,
        'available_users': available_users,
        'can_delegate': request.user.is_superuser,
    }
    return render(request, 'dossiers/members.html', context)


@login_required
@require_POST
def dossier_assign_member(request, slug):
    """
    Affecte un utilisateur à un dossier territorial avec un rôle local.
    """
    dossier = get_object_or_404(get_accessible_dossiers_for_user(request.user), slug=slug)
    user_id = request.POST.get('user_id')
    role = request.POST.get('role', 'observateur')

    target_user = get_object_or_404(User, id=user_id)

    try:
        assign_user_to_dossier(
            dossier=dossier,
            target_user=target_user,
            assigned_by=request.user,
            role=role,
        )
        messages.success(request, f"L'utilisateur {target_user.username} a été affecté à « {dossier.nom} » ({role}).")
    except PermissionDenied as e:
        messages.error(request, str(e))

    return redirect('dossiers:members', slug=dossier.slug)


@login_required
@require_POST
def dossier_revoke_member(request, slug, user_id):
    """
    Révoque l'accès d'un utilisateur à un dossier territorial.
    """
    dossier = get_object_or_404(get_accessible_dossiers_for_user(request.user), slug=slug)
    target_user = get_object_or_404(User, id=user_id)

    try:
        revoke_user_from_dossier(
            dossier=dossier,
            target_user=target_user,
            revoked_by=request.user,
        )
        messages.success(request, f"Accès révoqué pour {target_user.username} sur « {dossier.nom} ».")
    except PermissionDenied as e:
        messages.error(request, str(e))

    return redirect('dossiers:members', slug=dossier.slug)
