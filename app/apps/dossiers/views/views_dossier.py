from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dossiers.models import DossierMembership
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


def _get_target_dossier(request, slug=None):
    """Résout le dossier cible via request.active_dossier ou slug."""
    if hasattr(request, 'active_dossier') and request.active_dossier:
        return request.active_dossier
    if slug:
        return get_object_or_404(get_accessible_dossiers_for_user(request.user), slug=slug)
    active_id = request.session.get('active_dossier_id')
    if active_id:
        return get_object_or_404(get_accessible_dossiers_for_user(request.user), id=active_id)
    raise PermissionDenied("Aucun dossier sélectionné.")


@login_required
def dossier_select(request, slug):
    """
    Sélectionne un dossier comme espace de travail actif,
    mémorise le choix en session utilisateur et redirige vers le dashboard V2.
    """
    dossier = get_object_or_404(get_accessible_dossiers_for_user(request.user), slug=slug)

    request.session['active_dossier_id'] = str(dossier.id)
    request.session['active_dossier_slug'] = dossier.slug
    request.active_dossier = dossier
    messages.success(request, f"Espace de travail « {dossier.nom} » activé.")

    return redirect(f"/{dossier.slug}/dashboard/")


@login_required
def dossier_switch_clear(request):
    """
    Désélectionne le dossier actif en session pour revenir à la Galerie générale.
    """
    request.session.pop('active_dossier_id', None)
    request.session.pop('active_dossier_slug', None)
    if hasattr(request, 'active_dossier'):
        delattr(request, 'active_dossier')
    messages.info(request, "Retour à la sélection des territoires.")
    return redirect('dossiers:list')


@login_required
def dossier_members(request, slug=None):
    """
    Gestion des membres d'un dossier territorial.
    Accessible par le Superuser ou par l'Admin délégué sur ce dossier.
    """
    dossier = _get_target_dossier(request, slug)

    if not dossier.can_user_manage_members(request.user):
        raise PermissionDenied("Vous n'êtes pas habilité à gérer les membres de ce dossier.")

    memberships = get_dossier_members(dossier)

    # Statistiques KPI pour le header
    total_members = memberships.count()
    nb_admins = memberships.filter(role='admin').count()
    nb_operateurs = memberships.filter(role='operateur').count()
    nb_observateurs = memberships.filter(role='observateur').count()

    # Filtres de recherche & rôle
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()

    if q:
        memberships = memberships.filter(
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    if role_filter:
        memberships = memberships.filter(role=role_filter)

    existing_user_ids = memberships.values_list('user_id', flat=True)
    available_users = User.objects.filter(is_active=True).exclude(id__in=existing_user_ids).order_by('username')

    context = {
        'dossier': dossier,
        'memberships': memberships,
        'available_users': available_users,
        'can_delegate': request.user.is_superuser,
        'total_members': total_members,
        'nb_admins': nb_admins,
        'nb_operateurs': nb_operateurs,
        'nb_observateurs': nb_observateurs,
        'q': q,
        'role_filter': role_filter,
        'roles': DossierMembership.ROLE_CHOICES,
    }
    return render(request, 'dossiers/members.html', context)


@login_required
@require_POST
def dossier_assign_member(request, slug=None):
    """
    Affecte un utilisateur à un dossier territorial avec un rôle local.
    """
    dossier = _get_target_dossier(request, slug)
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

    return redirect(f"/{dossier.slug}/membres/")


@login_required
@require_POST
def dossier_revoke_member(request, user_id, slug=None):
    """
    Révoque l'accès d'un utilisateur à un dossier territorial.
    """
    dossier = _get_target_dossier(request, slug)
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

    return redirect(f"/{dossier.slug}/membres/")


@login_required
def dossier_create(request):
    """
    Création d'un nouveau dossier territorial (Workspace).
    Reçoit les données de l'assistant de configuration par étapes (Modal Wizard).
    """
    if not request.user.is_superuser and getattr(request.user, 'role', '') != 'admin':
        raise PermissionDenied("Seul un administrateur peut créer un nouveau dossier territorial.")

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        slug = request.POST.get('slug', '').strip() or None
        type_territoire = request.POST.get('type_territoire', 'commune')
        description = request.POST.get('description', '').strip()
        srid_metrique = int(request.POST.get('srid_metrique', 32628) or 32628)
        zoom_defaut = int(request.POST.get('zoom_defaut', 14) or 14)

        if not nom:
            messages.error(request, "Le nom du dossier est obligatoire.")
            return redirect('dossiers:list')

        # Configuration des modules métier activés
        modules_config = {
            'mod_espaces': request.POST.get('mod_espaces') == 'on',
            'mod_habitations': request.POST.get('mod_habitations') == 'on',
            'mod_urbanisme': request.POST.get('mod_urbanisme') == 'on',
            'mod_drones': request.POST.get('mod_drones') == 'on',
            'mod_signalements': request.POST.get('mod_signalements') == 'on',
            'mod_toponymie': request.POST.get('mod_toponymie') == 'on',
        }

        try:
            dossier = create_dossier(
                nom=nom,
                type_territoire=type_territoire,
                slug=slug,
                description=description,
                srid_metrique=srid_metrique,
                zoom_defaut=zoom_defaut,
                modules_config=modules_config,
                created_by=request.user,
            )
            # Sélection automatique du dossier nouvellement créé
            request.session['active_dossier_id'] = str(dossier.id)
            request.session['active_dossier_slug'] = dossier.slug
            request.active_dossier = dossier

            messages.success(request, f"Dossier territorial « {dossier.nom} » créé et activé avec succès.")
            return redirect(f"/{dossier.slug}/dashboard/")
        except Exception as e:
            messages.error(request, f"Erreur lors de la création du dossier : {e}")
            return redirect('dossiers:list')

    return redirect('dossiers:list')


@login_required
def dossier_settings(request, slug=None):
    """
    Paramètres et configuration des modules d'un dossier territorial actif.
    Accessible par le Superuser ou par l'Admin autorisé sur ce dossier.
    """
    dossier = _get_target_dossier(request, slug)

    if not (request.user.is_superuser or dossier.can_user_manage_members(request.user)):
        raise PermissionDenied("Vous n'êtes pas habilité à configurer ce dossier.")

    if request.method == 'POST':
        # 1. Mise à jour générale
        nom = request.POST.get('nom', '').strip()
        if nom:
            dossier.nom = nom
        dossier.description = request.POST.get('description', '').strip()
        dossier.type_territoire = request.POST.get('type_territoire', dossier.type_territoire)
        dossier.zoom_defaut = int(request.POST.get('zoom_defaut', dossier.zoom_defaut) or dossier.zoom_defaut)
        dossier.srid_metrique = int(request.POST.get('srid_metrique', dossier.srid_metrique) or dossier.srid_metrique)

        # 2. Modules métier activés
        modules_config = {
            'mod_espaces': request.POST.get('mod_espaces') == 'on',
            'mod_habitations': request.POST.get('mod_habitations') == 'on',
            'mod_urbanisme': request.POST.get('mod_urbanisme') == 'on',
            'mod_drones': request.POST.get('mod_drones') == 'on',
            'mod_signalements': request.POST.get('mod_signalements') == 'on',
            'mod_toponymie': request.POST.get('mod_toponymie') == 'on',
        }
        dossier.modules_config = modules_config

        # 3. Délégation superuser
        if request.user.is_superuser:
            role_gestionnaire = request.POST.get('role_gestionnaire_membres')
            if role_gestionnaire in ['superuser', 'admin']:
                dossier.role_gestionnaire_membres = role_gestionnaire

        dossier.save()
        messages.success(request, f"Configuration du dossier « {dossier.nom} » mise à jour avec succès.")
        return redirect(f"/{dossier.slug}/parametres/")

    context = {
        'dossier': dossier,
        'modules': dossier.modules_config if isinstance(dossier.modules_config, dict) else {},
        'can_delegate': request.user.is_superuser,
    }
    return render(request, 'dossiers/settings.html', context)
