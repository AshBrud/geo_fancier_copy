from .services_dossier import (
    create_dossier,
    assign_user_to_dossier,
    revoke_user_from_dossier,
    configure_dossier_modules,
    delegate_dossier_role,
)

__all__ = [
    'create_dossier',
    'assign_user_to_dossier',
    'revoke_user_from_dossier',
    'configure_dossier_modules',
    'delegate_dossier_role',
]
