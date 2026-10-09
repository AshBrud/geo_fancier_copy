"""
Service de registre et d'arborescence dynamique de navigation pour les espaces de travail (V2).
Génère pour chaque Dossier la structure hiérarchique à 2 niveaux (Groupes & Sous-groupes)
en filtrant selon les modules métier activés (modules_config), les habilitations RBAC de l'utilisateur,
et en calculant l'état accordéon (is_expanded, is_active).
"""

from typing import List, Dict, Any, Optional
from django.urls import reverse
from dossiers.services.services_terminology import get_term


def user_has_nav_permission(user, dossier, perm_code: str) -> bool:
    """
    Détermine si l'utilisateur détient la permission requise pour accéder à un élément de navigation,
    en combinant son statut global et son adhésion territoriale locale (DossierMembership).
    """
    if not user or not user.is_authenticated:
        return False

    # 1. Superuser souverain
    if user.is_superuser or getattr(user, 'role', None) in ['superuser', 'ROLE_SUPERUSER']:
        return True

    # 2. Évaluation contextuelle au Dossier actif
    if dossier:
        # Récupération du membership local
        membership = getattr(user, '_active_membership_cache', None)
        if membership is None or getattr(membership, 'dossier_id', None) != dossier.id:
            membership = dossier.memberships.filter(user=user).first()
            user._active_membership_cache = membership

        if membership:
            # Surcharges nominatives spécifiques au dossier
            if isinstance(membership.permissions_override, dict) and perm_code in membership.permissions_override:
                return bool(membership.permissions_override[perm_code])

            # Rôle Administrateur Territorial local
            if membership.role == 'admin':
                superuser_exclusive = {'dossier:delete', 'dossier:delegate_role', 'dossier:supervision'}
                return perm_code not in superuser_exclusive

            # Rôle Observateur local (lecture seule sans audit ni gestion utilisateurs)
            if membership.role == 'observateur':
                return perm_code.endswith(':view') and not (perm_code.startswith('users:') or perm_code.startswith('audit:'))

            # Rôle Opérateur local (permissions du profil opérateur)
            if membership.role == 'operateur':
                from accounts.models import Role
                op_role = Role.objects.filter(code='operateur').first()
                if op_role and op_role.permissions.filter(code=perm_code).exists():
                    return True

    # 3. Repli sur les permissions effectives globales du compte
    if hasattr(user, 'has_perm_name'):
        return user.has_perm_name(perm_code)

    return False


def get_workspace_navigation(dossier, current_path: str = '', user=None) -> List[Dict[str, Any]]:
    """
    Construit la liste ordonnée des groupes et sous-groupes de navigation
    pour un dossier donné, filtrée rigoureusement selon les modules activés
    et les prérogatives RBAC de l'utilisateur.
    """
    if not dossier:
        return []

    slug = dossier.slug
    modules = dossier.modules_config if isinstance(dossier.modules_config, dict) else {}

    groups = []

    # ─────────────────────────────────────────────────────────────
    # 1. TERRITOIRE & FONCIER (mod_espaces)
    # ─────────────────────────────────────────────────────────────
    if modules.get('mod_espaces', True):
        territoire_subitems = [
            {
                'slug': 'carte',
                'label': 'Cartographie SIG',
                'icon': 'bi-map',
                'url': f'/{slug}/territoire/carte/',
                'legacy_url': f'/{slug}/territoire/cartographie/',
                'required_perm': 'cadastre:view',
            },
            {
                'slug': 'zones',
                'label': get_term(dossier, 'zone_plural', 'Subdivisions & Secteurs'),
                'icon': 'bi-grid-3x3-gap',
                'url': f'/{slug}/territoire/zones/',
                'legacy_url': f'/{slug}/territoire/espaces/',
                'required_perm': 'cadastre:view',
            },
            {
                'slug': 'batiments',
                'label': get_term(dossier, 'bati_plural', 'Recensement Bâti'),
                'icon': 'bi-building',
                'url': f'/{slug}/territoire/batiments/',
                'required_perm': 'cadastre:view',
            },
            {
                'slug': 'reseaux',
                'label': get_term(dossier, 'reseau_plural', 'Réseaux Linéaires & Voies'),
                'icon': 'bi-signpost-split',
                'url': f'/{slug}/territoire/reseaux/',
                'legacy_url': f'/{slug}/territoire/voiries/',
                'required_perm': 'cadastre:view',
            },
            {
                'slug': 'suivi-travaux',
                'label': 'Suivi des Travaux',
                'icon': 'bi-hammer',
                'url': f'/{slug}/territoire/suivi-travaux/',
                'required_perm': 'cadastre:view',
            },
        ]

        # Filtrage RBAC des sous-items
        accessible_territoire = [
            sub for sub in territoire_subitems
            if not sub.get('required_perm') or user_has_nav_permission(user, dossier, sub['required_perm'])
        ]

        if accessible_territoire:
            groups.append({
                'key': 'territoire',
                'label': 'Territoire & Foncier',
                'icon': 'bi-geo-alt',
                'default_url': accessible_territoire[0]['url'],
                'subitems': accessible_territoire,
            })

    # ─────────────────────────────────────────────────────────────
    # 2. URBANISME & PLANIFICATION (mod_urbanisme)
    # ─────────────────────────────────────────────────────────────
    if modules.get('mod_urbanisme', True):
        urbanisme_subitems = [
            {
                'slug': 'constructions',
                'label': "Projets d'urbanisme",
                'icon': 'bi-building-add',
                'url': f'/{slug}/urbanisme/constructions/',
                'legacy_url': f'/{slug}/urbanisme/liste/',
                'required_perm': 'urbanisme:view',
            },
            {
                'slug': 'faisabilite',
                'label': 'Études & Faisabilité',
                'icon': 'bi-journal-check',
                'url': f'/{slug}/urbanisme/faisabilite/',
                'legacy_url': f'/{slug}/urbanisme/nouvelle/',
                'required_perm': 'urbanisme:simulate',
            },
            {
                'slug': 'historique',
                'label': 'Historique chantiers',
                'icon': 'bi-clock-history',
                'url': f'/{slug}/urbanisme/historique/',
                'required_perm': 'urbanisme:view',
            },
            {
                'slug': 'statistiques',
                'label': 'Statistiques foncières (PDU)',
                'icon': 'bi-bar-chart-line',
                'url': f'/{slug}/pdu/',
                'required_perm': 'urbanisme:view',
            },
        ]

        accessible_urbanisme = [
            sub for sub in urbanisme_subitems
            if not sub.get('required_perm') or user_has_nav_permission(user, dossier, sub['required_perm'])
        ]

        if accessible_urbanisme:
            groups.append({
                'key': 'urbanisme',
                'label': 'Urbanisme & Travaux',
                'icon': 'bi-building-gear',
                'default_url': accessible_urbanisme[0]['url'],
                'subitems': accessible_urbanisme,
            })

    # ─────────────────────────────────────────────────────────────
    # 4. DRONES & IMAGERIE (mod_drones)
    # ─────────────────────────────────────────────────────────────
    if modules.get('mod_drones', True):
        drones_subitems = [
            {
                'slug': 'missions',
                'label': 'Missions de vol',
                'icon': 'bi-send',
                'url': f'/{slug}/drones/missions/',
                'required_perm': 'drones:view',
            },
            {
                'slug': 'supervision',
                'label': 'Supervision SIG',
                'icon': 'bi-display',
                'url': f'/{slug}/drones/perspectives/',
                'required_perm': 'drones:view',
            },
            {
                'slug': 'enregistrements',
                'label': 'Enregistrements & Vidéos',
                'icon': 'bi-film',
                'url': f'/{slug}/drones/flux/videos/',
                'required_perm': 'drones:view',
            },
        ]

        accessible_drones = [
            sub for sub in drones_subitems
            if not sub.get('required_perm') or user_has_nav_permission(user, dossier, sub['required_perm'])
        ]

        if accessible_drones:
            groups.append({
                'key': 'drones',
                'label': 'Drones & Imagerie',
                'icon': 'bi-airplane',
                'default_url': accessible_drones[0]['url'],
                'subitems': accessible_drones,
            })

    # ─────────────────────────────────────────────────────────────
    # Calcul des états d'activation et de déploiement (Accordéon)
    # ─────────────────────────────────────────────────────────────
    clean_path = current_path.rstrip('/') + '/' if current_path else ''

    for group in groups:
        group_matches = False
        for sub in group['subitems']:
            target_url = sub['url'].rstrip('/') + '/'
            legacy_url = sub.get('legacy_url', '').rstrip('/') + '/' if sub.get('legacy_url') else None

            is_sub_active = (clean_path == target_url or (legacy_url and clean_path == legacy_url) or 
                             (len(target_url) > len(f'/{slug}/') and target_url in clean_path))
            sub['is_active'] = is_sub_active

            if is_sub_active:
                group_matches = True

        if f'/{slug}/{group["key"]}/' in clean_path:
            group_matches = True

        group['is_active'] = group_matches
        group['is_expanded'] = group_matches

    return groups

