from typing import Optional, Iterable, Tuple, Set
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import Permission, Role, UserPermissionLink, ActivityLog

User = get_user_model()


class RBACDelegationError(PermissionDenied):
    """Exception levée en cas de violation de la règle de délégation descendante (anti-escalade)."""
    pass


def validate_descendant_delegation(operator, requested_perms: Iterable[str]) -> None:
    """
    Règle mathématique de délégation descendante : P_demandée ⊆ P_opérateur
    Un Administrateur ne peut conférer à un compte subordonné (Standard)
    que des permissions qu'il détient lui-même.
    Le Superuser racine est exempté de cette restriction (maître absolu).
    """
    if operator.is_superuser or operator.role == Role.ROLE_SUPERUSER:
        return

    operator_perms: Set[str] = operator.get_effective_permissions()
    unauthorized = set(requested_perms) - operator_perms

    if unauthorized:
        unauthorized_list = ", ".join(sorted(unauthorized))
        raise RBACDelegationError(
            f"Violation anti-escalade : Vous ne disposez pas des permissions suivantes "
            f"et ne pouvez donc pas les déléguer : {unauthorized_list}"
        )


def can_manage_target_user(operator, target_user) -> Tuple[bool, str]:
    """
    Vérifie si l'opérateur a l'autorité institutionnelle requise pour modifier
    ou intervenir sur le compte cible.
    Règles de sécurité :
      1. Le Superuser peut agir sur tout le monde (sauf suppression de lui-même).
      2. Un Admin ne peut JAMAIS modifier ou désactiver un Superuser.
      3. Un Admin ne peut pas modifier un autre Admin (pas de peer-management horizontal).
      4. Un utilisateur ne peut pas se désactiver lui-même via les vues de gestion.
    """
    if operator.id == target_user.id:
        return False, "Vous ne pouvez pas effectuer cette opération sur votre propre compte."

    if target_user.is_superuser or target_user.role == Role.ROLE_SUPERUSER:
        return False, "Le compte Super Administrateur est protégé et immuable."

    if operator.is_superuser or operator.role == Role.ROLE_SUPERUSER:
        return True, ""

    if operator.role == Role.ROLE_ADMIN:
        if target_user.role == Role.ROLE_ADMIN:
            return False, "Un Administrateur ne peut pas administrer un pair Administrateur."
        return True, ""

    return False, "Vos prérogatives ne vous permettent pas d'administrer des utilisateurs."


@transaction.atomic
def create_managed_user(
    operator,
    username: str,
    email: str,
    password: str,
    role_code: str,
    first_name: str = "",
    last_name: str = "",
    telephone: str = "",
    custom_perm_codes: Optional[Iterable[str]] = None,
    ip_address: Optional[str] = None,
) -> User:
    """
    Création sécurisée d'un nouvel utilisateur avec traçabilité et garde-fous anti-escalade.
    """
    # 1. Contrôle d'éligibilité du créateur
    if not (operator.is_superuser or operator.has_perm_code('users:create')):
        raise PermissionDenied("Vous n'avez pas la permission de créer des utilisateurs (users:create requise).")

    # 2. Protection contre l'auto-élévation : seul le Superuser peut créer un Admin
    if role_code in [Role.ROLE_ADMIN, Role.ROLE_SUPERUSER]:
        if not (operator.is_superuser or operator.role == Role.ROLE_SUPERUSER):
            raise PermissionDenied("Seul le Super Administrateur peut désigner un Administrateur Territorial.")

    if role_code == Role.ROLE_SUPERUSER:
        raise PermissionDenied("Le Super Administrateur racine ne peut pas être dupliqué via l'interface.")

    # 3. Validation de délégation sur les permissions personnalisées
    if custom_perm_codes:
        validate_descendant_delegation(operator, custom_perm_codes)

    # 4. Résolution du rôle assigné
    role_obj = Role.objects.filter(code=role_code).first()

    # 5. Création du compte
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role_code,
        assigned_role=role_obj,
        created_by=operator,
        telephone=telephone,
        is_active=True,
    )

    # 6. Enregistrement des éventuelles surcharges de permissions
    if custom_perm_codes:
        perms = Permission.objects.filter(code__in=custom_perm_codes)
        links = [UserPermissionLink(user=user, permission=p, is_granted=True) for p in perms]
        UserPermissionLink.objects.bulk_create(links)

    # 7. Audit log
    ActivityLog.objects.create(
        user=operator,
        action="CREATION_UTILISATEUR",
        detail=f"Création du compte '{user.username}' avec le rôle '{role_code}'.",
        ip_address=ip_address,
    )

    return user


@transaction.atomic
def soft_delete_user(operator, target_user, ip_address: Optional[str] = None) -> None:
    """
    Désactivation logique irréversible par les pairs, maintenant l'intégrité de l'ActivityLog.
    """
    allowed, message = can_manage_target_user(operator, target_user)
    if not allowed:
        raise PermissionDenied(message)

    if not (operator.is_superuser or operator.has_perm_code('users:deactivate')):
        raise PermissionDenied("Permission 'users:deactivate' manquante pour désactiver ce compte.")

    target_user.is_active = False
    target_user.save(update_fields=['is_active'])

    ActivityLog.objects.create(
        user=operator,
        action="DESACTIVATION_UTILISATEUR",
        detail=f"Désactivation logique du compte '{target_user.username}' ({target_user.get_role_display()}).",
        ip_address=ip_address,
    )
