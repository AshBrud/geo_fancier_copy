from typing import Optional, Dict, Any
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from dossiers.models import Dossier, DossierMembership


@transaction.atomic
def create_dossier(
    nom: str,
    type_territoire: str = 'commune',
    slug: Optional[str] = None,
    description: str = '',
    geometrie=None,
    srid_metrique: int = 32628,
    zoom_defaut: int = 14,
    modules_config: Optional[Dict[str, bool]] = None,
    role_gestionnaire_membres: str = 'admin',
    created_by=None,
) -> Dossier:
    """
    Crée un nouveau dossier territorial (Workspace).
    Optionnellement, associe immédiatement le créateur comme administrateur du dossier.
    """
    dossier = Dossier(
        nom=nom,
        type_territoire=type_territoire,
        slug=slug or '',
        description=description,
        geometrie=geometrie,
        srid_metrique=srid_metrique,
        zoom_defaut=zoom_defaut,
        role_gestionnaire_membres=role_gestionnaire_membres,
    )
    if modules_config:
        dossier.modules_config = modules_config

    dossier.save()

    # Si le créateur est renseigné et n'est pas superuser, on lui attribue une adhésion admin
    if created_by and created_by.is_authenticated:
        DossierMembership.objects.get_or_create(
            user=created_by,
            dossier=dossier,
            defaults={
                'role': 'admin',
                'assigned_by': created_by,
            }
        )

    return dossier


@transaction.atomic
def assign_user_to_dossier(
    dossier: Dossier,
    target_user,
    assigned_by,
    role: str = 'observateur',
    permissions_override: Optional[Dict[str, Any]] = None,
) -> DossierMembership:
    """
    Affecte un utilisateur à un dossier territorial avec traçabilité complète.
    Contrôle de sécurité :
    - Le Superuser peut affecter n'importe quel compte.
    - Un Admin ne peut affecter que s'il est gestionnaire autorisé sur ce dossier.
    """
    if not assigned_by or not assigned_by.is_authenticated:
        raise PermissionDenied("Authentification requise pour affecter des membres.")

    # Contrôle du droit d'affectation
    if not dossier.can_user_manage_members(assigned_by):
        raise PermissionDenied(
            f"L'utilisateur {assigned_by} n'est pas habilité à affecter des membres au dossier '{dossier.nom}'."
        )

    membership, created = DossierMembership.objects.update_or_create(
        user=target_user,
        dossier=dossier,
        defaults={
            'role': role,
            'assigned_by': assigned_by,
            'permissions_override': permissions_override or {},
        }
    )
    return membership


@transaction.atomic
def revoke_user_from_dossier(
    dossier: Dossier,
    target_user,
    revoked_by,
) -> bool:
    """
    Révoque l'accès d'un utilisateur à un dossier territorial.
    Contrôle de sécurité :
    - Vérifie que révoqué != superuser.
    - Vérifie l'habilitation de revoked_by.
    """
    if not revoked_by or not revoked_by.is_authenticated:
        raise PermissionDenied("Authentification requise pour révoquer des membres.")

    if not dossier.can_user_manage_members(revoked_by):
        raise PermissionDenied("Vous n'êtes pas habilité à révoquer des accès sur ce dossier.")

    membership = DossierMembership.objects.filter(user=target_user, dossier=dossier).first()
    if membership:
        membership.delete()
        return True
    return False


@transaction.atomic
def configure_dossier_modules(
    dossier: Dossier,
    modules_config: Dict[str, bool],
    configured_by,
) -> Dossier:
    """
    Met à jour les modules activés pour un dossier (ex: mod_drones, mod_urbanisme).
    """
    if not configured_by or not (configured_by.is_superuser or dossier.can_user_manage_members(configured_by)):
        raise PermissionDenied("Non autorisé à modifier la configuration des modules de ce dossier.")

    dossier.modules_config = modules_config
    dossier.save(update_fields=['modules_config', 'date_modification'])
    return dossier


@transaction.atomic
def delegate_dossier_role(
    dossier: Dossier,
    role_gestionnaire: str,
    delegated_by,
) -> Dossier:
    """
    Configure le rôle délégué ayant la responsabilité d'affecter les membres à ce dossier.
    RÉSERVÉ EXCLUSIVEMENT AU SUPERUSER (Souveraineté d'État).
    """
    if not delegated_by or not delegated_by.is_superuser:
        raise PermissionDenied("Seul le Superuser peut déléguer le rôle de gestion des membres.")

    dossier.role_gestionnaire_membres = role_gestionnaire
    dossier.save(update_fields=['role_gestionnaire_membres', 'date_modification'])
    return dossier
