from .views_cartographie import cartographie
from .views_zone_secteur import (
    zones_secteurs_list,
    zone_secteur_detail,
    zone_secteur_create,
    zone_secteur_update,
    zone_secteur_delete,
)
from .views_unite_batie import (
    unites_baties_list,
    unite_batie_detail,
    unite_batie_create,
    unite_batie_update,
    unite_batie_delete,
    unite_batie_import_sig,
)
from .views_reseau_lineaire import (
    reseaux_lineaires_list,
    reseau_lineaire_detail,
    reseau_lineaire_create,
    reseau_lineaire_update,
    reseau_lineaire_delete,
)
from .views_suivi_travaux import (
    suivi_travaux_list,
    suivi_travaux_update,
)

__all__ = [
    'cartographie',
    'zones_secteurs_list',
    'zone_secteur_detail',
    'zone_secteur_create',
    'zone_secteur_update',
    'zone_secteur_delete',
    'unites_baties_list',
    'unite_batie_detail',
    'unite_batie_create',
    'unite_batie_update',
    'unite_batie_delete',
    'unite_batie_import_sig',
    'reseaux_lineaires_list',
    'reseau_lineaire_detail',
    'reseau_lineaire_create',
    'reseau_lineaire_update',
    'reseau_lineaire_delete',
    'suivi_travaux_list',
    'suivi_travaux_update',
]
