import datetime
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.models import CustomUser, ActivityLog, Role, Permission
from accounts.forms import AdminCreationForm, StandardUserCreationForm, UnifiedUserCreationForm, UserUpdateForm, UserUpdateModalForm
from accounts.decorators import admin_required, require_permission
from accounts.services.services_rbac import create_managed_user, soft_delete_user, activate_user, can_manage_target_user
from dossiers.models import Dossier, DossierMembership
from dossiers.services.services_dossier import assign_user_to_dossier


@login_required
@admin_required
def users_list(request):
    qs = CustomUser.objects.prefetch_related('dossier_memberships__dossier').select_related('created_by')
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
    is_super = request.user.is_superuser or request.user.role == 'superuser'

    # Dossiers disponibles pour rattachement initial
    if is_super:
        available_dossiers = Dossier.objects.filter(is_active=True).order_by('nom')
    else:
        admin_dossier_ids = DossierMembership.objects.filter(
            user=request.user,
            role='admin'
        ).values_list('dossier_id', flat=True)
        available_dossiers = Dossier.objects.filter(id__in=admin_dossier_ids, is_active=True).order_by('nom')

    # Catalogue des permissions groupées par domaine métier
    all_permissions = Permission.objects.all().order_by('domaine', 'code')
    permissions_by_domain = {}
    domain_labels = dict(Permission.DOMAINES)
    for p in all_permissions:
        d_code = p.domaine
        if d_code not in permissions_by_domain:
            permissions_by_domain[d_code] = {
                'label': domain_labels.get(d_code, d_code.capitalize()),
                'permissions': []
            }
        permissions_by_domain[d_code]['permissions'].append(p)

    # Initialisation / vérification des 4 rôles RBAC avec leurs permissions de base si vides
    # 1. Rôle Plafond Standard
    role_standard, _ = Role.objects.get_or_create(
        code='standard',
        defaults={'nom': 'Plafond Type Standard', 'description': 'Enveloppe maximale des prérogatives autorisées pour les comptes de type Standard.', 'is_canonical': True}
    )
    if not role_standard.permissions.exists():
        role_standard.permissions.set([
            p for p in all_permissions
            if not (
                p.code.startswith('users:') or
                p.code.startswith('audit:') or
                p.code in {
                    'dossier:delete', 'dossier:delegate_role', 'dossier:supervision',
                    'dossier:create', 'dossier:configure_modules',
                    'dossier:assign_members', 'dossier:revoke_members', 'dossier:update',
                }
            )
        ])

    # 2. Rôle Admin Territorial
    role_admin, _ = Role.objects.get_or_create(
        code='admin',
        defaults={'nom': 'Administrateur Territorial', 'description': 'Délégué institutionnel sur un territoire.', 'is_canonical': True}
    )
    if not role_admin.permissions.exists():
        role_admin.permissions.set([
            p for p in all_permissions
            if p.code not in {'dossier:delegate_role', 'dossier:supervision', 'dossier:delete'}
        ])

    # 3. Rôle Opérateur SIG (Standard)
    role_op, _ = Role.objects.get_or_create(
        code='operateur',
        defaults={'nom': 'Opérateur SIG / Technicien', 'description': 'Agent de terrain habilité à la saisie foncière.', 'is_canonical': False}
    )
    if not role_op.permissions.exists():
        role_op.permissions.set([
            p for p in all_permissions
            if p.code in {
                'dossier:view',
                'cadastre:view', 'cadastre:manage_parcelles', 'cadastre:manage_voiries',
                'cadastre:manage_zones', 'cadastre:manage_espaces_verts',
                'habitations:view', 'habitations:create', 'habitations:update',
                'signalements:view', 'signalements:create', 'signalements:manage',
                'drones:view', 'drones:upload_photos',
                'urbanisme:view', 'urbanisme:create_projet',
                'toponymie:view', 'toponymie:manage',
            }
        ])

    # 4. Rôle Observateur (Standard)
    role_obs, _ = Role.objects.get_or_create(
        code='observateur',
        defaults={'nom': 'Observateur (Consultation)', 'description': 'Profil en consultation seule sans droits de modification.', 'is_canonical': False}
    )
    if not role_obs.permissions.exists():
        role_obs.permissions.set([
            p for p in all_permissions
            if p.code.endswith(':view') and not (p.code.startswith('users:') or p.code.startswith('audit:'))
        ])

    # Matrice actuelle { role_code: [permission_codes] }
    roles_matrix = {
        'admin': list(role_admin.permissions.values_list('code', flat=True)),
        'standard': list(role_standard.permissions.values_list('code', flat=True)),
        'operateur': list(role_op.permissions.values_list('code', flat=True)),
        'observateur': list(role_obs.permissions.values_list('code', flat=True)),
    }

    operator_effective_perms = list(all_permissions.values_list('code', flat=True)) if is_super else list(request.user.get_effective_permissions())

    context = {
        'page_obj': page,
        'q': q, 'role_filter': role_filter, 'statut_filter': statut_filter,
        'roles': CustomUser.CANONICAL_ROLES_CHOICES,
        'total_users': CustomUser.objects.count(),
        'nb_actifs': CustomUser.objects.filter(is_active=True).count(),
        'nb_admins': CustomUser.objects.filter(role__in=[CustomUser.ROLE_ADMIN, 'admin']).count(),
        'nb_recents': CustomUser.objects.filter(last_login__gte=seuil_recent).count(),
        'is_super': is_super,
        'available_dossiers': available_dossiers,
        'permissions_by_domain': permissions_by_domain,
        'roles_matrix_json': json.dumps(roles_matrix),
        'operator_perms_json': json.dumps(operator_effective_perms),
    }
    return render(request, 'accounts/management/list.html', context)


@login_required
@require_permission('users:create')
def user_create(request):
    """
    Création unifiée d'un utilisateur via la modale d'administration (en 3 étapes).
    Traite le type de compte (contrôle anti-escalade), l'identité et l'accès multi-territoires.
    Redirige les requêtes GET directement vers la galerie des utilisateurs.
    """
    if request.method == 'POST':
        form = UnifiedUserCreationForm(request.POST, operator=request.user)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                user = create_managed_user(
                    operator=request.user,
                    username=cd['username'],
                    email=cd['email'],
                    password=cd['password'],
                    role_code=cd['role'],
                    first_name=cd.get('first_name', ''),
                    last_name=cd.get('last_name', ''),
                    telephone=cd.get('telephone', ''),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )

                # Résolution du rôle territorial (admin forcé si type admin, sinon opérateur/observateur)
                dossier_role = cd.get('dossier_role') or ('admin' if cd['role'] == 'admin' else 'operateur')
                affectation_mode = cd.get('affectation_mode', 'all')

                if affectation_mode == 'all':
                    # 1. Accès universel (actuels et futurs)
                    user.acces_tous_territoires = True
                    user.save(update_fields=['acces_tous_territoires'])

                    # Rattachement formel à tous les dossiers actifs existants
                    active_dossiers = Dossier.objects.filter(is_active=True)
                    count_assigned = 0
                    for d in active_dossiers:
                        DossierMembership.objects.update_or_create(
                            user=user,
                            dossier=d,
                            defaults={
                                'role': dossier_role,
                                'assigned_by': request.user,
                            }
                        )
                        count_assigned += 1

                    messages.success(
                        request,
                        f"Compte '{user.username}' créé avec succès [{user.get_role_display()}] avec accès universel (actuels et futurs, rôle : {dossier_role})."
                    )

                elif affectation_mode == 'selection':
                    # 2. Sélection ciblée de territoires
                    selected_ids = request.POST.getlist('dossier_ids')
                    count_assigned = 0
                    if selected_ids:
                        target_dossiers = Dossier.objects.filter(id__in=selected_ids, is_active=True)
                        for d in target_dossiers:
                            DossierMembership.objects.update_or_create(
                                user=user,
                                dossier=d,
                                defaults={
                                    'role': dossier_role,
                                    'assigned_by': request.user,
                                }
                            )
                            count_assigned += 1

                    messages.success(
                        request,
                        f"Compte '{user.username}' créé avec succès [{user.get_role_display()}] et rattaché à {count_assigned} territoire(s) (rôle : {dossier_role})."
                    )

                else:
                    messages.success(request, f"Compte '{user.username}' créé avec succès [{user.get_role_display()}].")

                return redirect('accounts:users')

            except Exception as e:
                messages.error(request, f"Erreur lors de la création de l'utilisateur : {e}")
                return redirect('accounts:users')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field.capitalize()} : {err}")
            return redirect('accounts:users')

    return redirect('accounts:users')


@login_required
@require_permission('users:update')
def user_update(request, pk):
    """
    Mise à jour d'un compte utilisateur via la modale d'édition.
    Traite l'identité, le type de compte, le mot de passe optionnel, le statut et les affectations territoriales.
    Redirige les requêtes GET directement vers la liste des utilisateurs.
    """
    target_user = get_object_or_404(CustomUser, pk=pk)

    # Règle d'inviolabilité absolue : Un compte Super Administrateur ne peut JAMAIS être modifié,
    # même par lui-même depuis l'interface de gestion des comptes.
    if target_user.is_superuser or target_user.role in [Role.ROLE_SUPERUSER, 'superuser']:
        messages.error(
            request,
            "Règle de gouvernance : Le compte Super Administrateur est souverain, protégé et immuable. Ses informations ne peuvent pas être modifiées."
        )
        return redirect('accounts:users')

    allowed, msg = can_manage_target_user(request.user, target_user)
    if not allowed:
        messages.error(request, msg)
        return redirect('accounts:users')

    if request.method == 'POST':
        form = UserUpdateModalForm(
            request.POST,
            operator=request.user,
            target_user=target_user
        )
        if form.is_valid():
            cd = form.cleaned_data
            try:
                target_user.first_name = cd['first_name']
                target_user.last_name = cd['last_name']
                target_user.email = cd['email']
                target_user.telephone = cd.get('telephone', '')
                target_user.is_active = cd.get('is_active', True)

                # Modification du type de compte (uniquement si Superuser et pas de cible Superuser)
                is_operator_super = request.user.is_superuser or request.user.role == 'superuser'
                is_target_super = target_user.is_superuser or target_user.role == 'superuser'
                if is_operator_super and not is_target_super:
                    new_role = cd.get('role')
                    if new_role in [Role.ROLE_ADMIN, Role.ROLE_STANDARD]:
                        target_user.role = new_role
                        role_obj = Role.objects.filter(code=new_role).first()
                        target_user.assigned_role = role_obj

                # Modification du mot de passe (uniquement si renseigné)
                new_pwd = cd.get('password')
                if new_pwd:
                    target_user.set_password(new_pwd)
                    target_user.must_change_password = True

                # Synchronisation du périmètre territorial
                affectation_mode = cd.get('affectation_mode') or request.POST.get('affectation_mode') or ('all' if target_user.acces_tous_territoires else 'selection')
                dossier_role = cd.get('dossier_role') or ('admin' if target_user.role == 'admin' else 'operateur')

                if affectation_mode == 'all':
                    target_user.acces_tous_territoires = True
                    for d in Dossier.objects.filter(is_active=True):
                        DossierMembership.objects.update_or_create(
                            user=target_user,
                            dossier=d,
                            defaults={
                                'role': dossier_role,
                                'assigned_by': request.user,
                            }
                        )
                elif affectation_mode == 'selection':
                    target_user.acces_tous_territoires = False
                    selected_ids = request.POST.getlist('dossier_ids')
                    # Retirer les adhésions aux dossiers non cochés
                    DossierMembership.objects.filter(user=target_user).exclude(dossier_id__in=selected_ids).delete()
                    # Assigner les dossiers cochés avec le rôle choisi
                    if selected_ids:
                        for d in Dossier.objects.filter(id__in=selected_ids, is_active=True):
                            DossierMembership.objects.update_or_create(
                                user=target_user,
                                dossier=d,
                                defaults={
                                    'role': dossier_role,
                                    'assigned_by': request.user,
                                }
                            )
                else:
                    target_user.acces_tous_territoires = False
                    DossierMembership.objects.filter(user=target_user).delete()

                target_user.save()

                ActivityLog.objects.create(
                    user=request.user,
                    action="MODIFICATION_UTILISATEUR",
                    detail=f"Mise à jour des attributs du compte '{target_user.username}'.",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, f"Utilisateur '{target_user.username}' mis à jour avec succès.")
                return redirect('accounts:users')

            except Exception as e:
                messages.error(request, f"Erreur lors de la mise à jour : {e}")
                return redirect('accounts:users')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field.capitalize()} : {err}")
            return redirect('accounts:users')

    return redirect('accounts:users')


@login_required
@require_permission('users:deactivate')
def user_delete(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)

    if target_user.is_superuser or target_user.role in [Role.ROLE_SUPERUSER, 'superuser']:
        messages.error(
            request,
            "Règle de gouvernance : Le compte Super Administrateur est souverain et ne peut en aucun cas être désactivé ou supprimé."
        )
        return redirect('accounts:users')

    is_target_admin = (target_user.role in [Role.ROLE_ADMIN, 'admin']) or getattr(target_user, 'is_admin', False)
    is_operator_super = request.user.is_superuser or request.user.role in [Role.ROLE_SUPERUSER, 'superuser']
    if is_target_admin and not is_operator_super:
        messages.error(request, "Action interdite : Seul le Super Administrateur est habilité à désactiver un compte Administrateur Territorial.")
        return redirect('accounts:users')

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
@require_permission('users:update')
def user_activate(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)

    if target_user.is_superuser or target_user.role in [Role.ROLE_SUPERUSER, 'superuser']:
        messages.error(request, "Règle de gouvernance : Le compte Super Administrateur est souverain et toujours actif.")
        return redirect('accounts:users')

    is_target_admin = (target_user.role in [Role.ROLE_ADMIN, 'admin']) or getattr(target_user, 'is_admin', False)
    is_operator_super = request.user.is_superuser or request.user.role in [Role.ROLE_SUPERUSER, 'superuser']
    if is_target_admin and not is_operator_super:
        messages.error(request, "Action interdite : Seul le Super Administrateur est habilité à réactiver un compte Administrateur Territorial.")
        return redirect('accounts:users')

    allowed, message = can_manage_target_user(request.user, target_user)
    if not allowed:
        messages.error(request, f"Action interdite : {message}")
        return redirect('accounts:users')

    if request.method == 'POST':
        try:
            activate_user(
                operator=request.user,
                target_user=target_user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Le compte de l'utilisateur '{target_user.username}' a été réactivé avec succès.")
            return redirect('accounts:users')
        except Exception as e:
            messages.error(request, f"Erreur lors de la réactivation : {e}")
            return redirect('accounts:users')

    return redirect('accounts:users')



@login_required
@require_permission('audit:view')
def activity_log(request):
    logs = ActivityLog.objects.select_related('user').all()[:200]
    return render(request, 'accounts/management/activity_log.html', {'logs': logs})


@login_required
def roles_matrix_manage(request):
    """
    Gestion centralisée de la matrice des permissions des rôles RBAC :
    - admin : modifiable exclusivement par le Super Administrateur.
    - standard, operateur, observateur : modifiables par le Superuser ou les Administrateurs (avec délégation descendante).
    """
    is_super = request.user.is_superuser or request.user.role == 'superuser'
    is_admin = is_super or request.user.role == 'admin' or request.user.is_admin

    if not is_admin:
        messages.error(request, "Accès refusé. Privilèges d'administration requis.")
        return redirect('accounts:users')

    if request.method == 'POST':
        target_role_code = request.POST.get('target_role')
        if not target_role_code:
            messages.error(request, "Rôle cible non spécifié.")
            return redirect('accounts:users')

        # 1. Protection du rôle Admin
        if target_role_code == 'admin' and not is_super:
            messages.error(request, "Action interdite : Seul le Super Administrateur peut modifier les permissions du rôle Administrateur Territorial.")
            return redirect('accounts:users')

        # 2. Interdiction absolue de manipuler le superuser
        if target_role_code in ['superuser', Role.ROLE_SUPERUSER]:
            messages.error(request, "Le compte et le rôle Super Administrateur sont souverains et immuables.")
            return redirect('accounts:users')

        selected_perms = request.POST.getlist('permissions')

        # 3. Règle de délégation descendante (Anti-escalade) pour les Admins
        if not is_super:
            operator_perms = request.user.get_effective_permissions()
            unauthorized = set(selected_perms) - operator_perms
            if unauthorized:
                unauth_str = ", ".join(sorted(unauthorized))
                messages.error(request, f"Délégation interdite : Vous ne pouvez pas accorder des permissions hors de votre propre périmètre habilité ({unauth_str}).")
                return redirect('accounts:users')

        # 4. Règle d'enveloppe : operateur et observateur ne peuvent pas dépasser le plafond 'standard'
        if target_role_code in ['operateur', 'observateur']:
            standard_role = Role.objects.filter(code='standard').first()
            if standard_role:
                std_perms = set(standard_role.permissions.values_list('code', flat=True))
                overflow = set(selected_perms) - std_perms
                if overflow:
                    overflow_str = ", ".join(sorted(overflow))
                    messages.error(request, f"Incohérence hiérarchique : Ces permissions dépassent l'enveloppe maximale autorisée pour le type Standard : {overflow_str}")
                    return redirect('accounts:users')

        # 5. Règle d'étanchéité du Plafond Standard : interdiction absolue des permissions administratives
        if target_role_code == 'standard':
            admin_exclusive = {
                'audit:view', 'audit:export',
                'users:view', 'users:create', 'users:update', 'users:deactivate', 'users:reset_password',
                'dossier:create', 'dossier:delete', 'dossier:delegate_role', 'dossier:supervision', 'dossier:configure_modules',
                'dossier:assign_members', 'dossier:revoke_members', 'dossier:update',
            }
            forbidden_in_standard = set(selected_perms).intersection(admin_exclusive)
            if forbidden_in_standard:
                forbid_str = ", ".join(sorted(forbidden_in_standard))
                messages.error(request, f"Séparation des pouvoirs : Les permissions suivantes sont strictement réservées aux Administrateurs et ne peuvent intégrer le Plafond Standard : {forbid_str}")
                return redirect('accounts:users')

        # 6. Règle souveraine pour le rôle Admin : interdiction des exclusivités Super Administrateur
        if target_role_code == 'admin':
            superuser_exclusive = {'dossier:delete', 'dossier:delegate_role', 'dossier:supervision'}
            forbidden_in_admin = set(selected_perms).intersection(superuser_exclusive)
            if forbidden_in_admin:
                forbid_str = ", ".join(sorted(forbidden_in_admin))
                messages.error(request, f"Exclusivité souveraine : Ces permissions sont réservées au Super Administrateur : {forbid_str}")
                return redirect('accounts:users')

        # 7. Règle de consultation seule pour l'Observateur
        if target_role_code == 'observateur':
            invalid_obs = [p for p in selected_perms if not p.endswith(':view') or p.startswith('users:') or p.startswith('audit:')]
            if invalid_obs:
                invalid_obs_str = ", ".join(sorted(invalid_obs))
                messages.error(request, f"Profil en lecture seule : Le rôle Observateur ne peut recevoir que des permissions de consultation territoriale (:view hors audit et gestion d'utilisateurs). Rejet de : {invalid_obs_str}")
                return redirect('accounts:users')

        role_obj = Role.objects.filter(code=target_role_code).first()
        if not role_obj:
            messages.error(request, f"Rôle '{target_role_code}' introuvable.")
            return redirect('accounts:users')

        # Application des permissions
        perms_to_set = Permission.objects.filter(code__in=selected_perms)
        role_obj.permissions.set(perms_to_set)

        # Si on met à jour le Plafond Standard, épurer automatiquement les sous-rôles pour garantir l'enveloppe
        if target_role_code == 'standard':
            for sub_role in Role.objects.filter(code__in=['operateur', 'observateur']):
                invalid_sub_perms = sub_role.permissions.exclude(id__in=perms_to_set.values_list('id', flat=True))
                if invalid_sub_perms.exists():
                    sub_role.permissions.remove(*invalid_sub_perms)

        ActivityLog.objects.create(
            user=request.user,
            action="MODIFICATION_ROLE_RBAC",
            detail=f"Mise à jour des permissions du rôle '{role_obj.nom}' ({perms_to_set.count()} permissions configurées).",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(
            request,
            f"Les permissions du rôle « {role_obj.nom} » ont été enregistrées avec succès ({perms_to_set.count()} permissions accordées). Tous les utilisateurs rattachés en bénéficient immédiatement."
        )
        return redirect('accounts:users')

    return redirect('accounts:users')

