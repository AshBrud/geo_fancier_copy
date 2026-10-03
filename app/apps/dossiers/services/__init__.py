from .services_dossier import (
    create_dossier,
    assign_user_to_dossier,
    revoke_user_from_dossier,
    configure_dossier_modules,
    delegate_dossier_role,
)
from .service_navigation import get_workspace_navigation
from .services_terminology import (
    get_term,
    get_dossier_lexicon,
    resolve_space_type,
)

__all__ = [
    'create_dossier',
    'assign_user_to_dossier',
    'revoke_user_from_dossier',
    'configure_dossier_modules',
    'delegate_dossier_role',
    'get_workspace_navigation',
    'get_term',
    'get_dossier_lexicon',
    'resolve_space_type',
]
