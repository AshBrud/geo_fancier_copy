"""
Context Processors pour l'application Dossiers.
Injecte automatiquement dans tous les templates Django le dossier actif en session,
ses modules activés et la liste des dossiers accessibles pour le switcher rapide.
"""

from typing import Dict, Any
from dossiers.selectors import (
    get_accessible_dossiers_for_user,
    get_dossier_by_id,
    get_dossier_by_slug,
    get_user_membership,
)


def active_dossier_context(request) -> Dict[str, Any]:
    """
    Injecte :
    - active_dossier: l'instance Dossier active sélectionnée par l'utilisateur.
    - active_membership: l'adhésion DossierMembership de l'utilisateur sur ce dossier.
    - active_modules: dictionnaire des booléens des modules activés (mod_espaces, etc.).
    - user_accessible_dossiers: liste des dossiers accessibles pour le menu contextuel.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'active_dossier': None,
            'active_membership': None,
            'active_modules': {},
            'user_accessible_dossiers': [],
        }

    accessible_dossiers = get_accessible_dossiers_for_user(request.user)

    # Récupérer l'identifiant du dossier actif stocké en session
    active_dossier_id = request.session.get('active_dossier_id')
    active_dossier = None

    if active_dossier_id:
        active_dossier = get_dossier_by_id(active_dossier_id)

    # Si l'utilisateur n'a accès qu'à un seul dossier et aucun n'est sélectionné, l'activer par défaut
    if not active_dossier and accessible_dossiers.count() == 1:
        active_dossier = accessible_dossiers.first()
        if active_dossier:
            request.session['active_dossier_id'] = str(active_dossier.id)

    # Vérification de sécurité : si le dossier actif n'est plus accessible pour cet utilisateur
    if active_dossier and not request.user.is_superuser:
        if not accessible_dossiers.filter(id=active_dossier.id).exists():
            active_dossier = None
            request.session.pop('active_dossier_id', None)

    active_membership = None
    if active_dossier:
        active_membership = get_user_membership(request.user, active_dossier)

    active_modules = active_dossier.modules_config if active_dossier else {}

    return {
        'active_dossier': active_dossier,
        'active_membership': active_membership,
        'active_modules': active_modules,
        'user_accessible_dossiers': accessible_dossiers,
    }
