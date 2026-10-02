import uuid
from typing import Optional
from django.db.models import QuerySet
from dossiers.models import Dossier, DossierMembership


def get_all_dossiers() -> QuerySet[Dossier]:
    """Retourne la totalité des dossiers sans filtre."""
    return Dossier.objects.all().order_by('nom')


def get_active_dossiers() -> QuerySet[Dossier]:
    """Retourne l'ensemble des dossiers actifs dans le système."""
    return Dossier.objects.filter(is_active=True).order_by('nom')


def get_accessible_dossiers_for_user(user) -> QuerySet[Dossier]:
    """
    Retourne la liste des dossiers auxquels un utilisateur a légitimement accès :
    - Superuser : accès souverain à TOUS les dossiers actifs.
    - Admin ou Standard : accès restreint aux dossiers avec adhésion formelle (DossierMembership).
    """
    if not user or not user.is_authenticated:
        return Dossier.objects.none()

    if user.is_superuser:
        return get_active_dossiers()

    return Dossier.objects.filter(
        is_active=True,
        memberships__user=user
    ).distinct().order_by('nom')


def get_dossier_by_slug(slug: str) -> Optional[Dossier]:
    """Récupère un dossier à partir de son slug unique."""
    return Dossier.objects.filter(slug=slug).first()


def get_dossier_by_id(dossier_id: uuid.UUID) -> Optional[Dossier]:
    """Récupère un dossier à partir de son UUID primaire."""
    return Dossier.objects.filter(id=dossier_id).first()


def get_user_membership(user, dossier: Dossier) -> Optional[DossierMembership]:
    """Récupère l'adhésion d'un utilisateur à un dossier précis."""
    if not user or not user.is_authenticated or not dossier:
        return None
    return DossierMembership.objects.filter(user=user, dossier=dossier).select_related('user', 'assigned_by').first()


def get_dossier_members(dossier: Dossier) -> QuerySet[DossierMembership]:
    """Retourne la liste de tous les membres rattachés à un dossier avec préchargement."""
    if not dossier:
        return DossierMembership.objects.none()
    return DossierMembership.objects.filter(dossier=dossier).select_related('user', 'assigned_by').order_by('role', 'user__username')
