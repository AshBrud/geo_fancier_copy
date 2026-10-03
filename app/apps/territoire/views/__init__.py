from .views_cartographie import cartographie
from .views_espace import (
    espaces_list,
    campus_detail,
    espace_detail,
    espace_create,
    espace_update,
    espace_delete,
)
from .views_batiment import (
    batiments_list,
    batiment_detail,
    batiment_create,
    batiment_update,
    batiment_delete,
    batiment_import_sig,
)
from .views_terrain import (
    terrains_list,
    terrain_detail,
    terrain_create,
    terrain_update,
    terrain_delete,
)
from .views_voirie import (
    voiries_list,
    voirie_detail,
    voirie_create,
    voirie_update,
    voirie_delete,
    espaces_verts_list,
    espace_vert_detail,
    espace_vert_create,
    espace_vert_update,
    espace_vert_delete,
)
from .views_suivi_travaux import (
    suivi_travaux_list,
    suivi_travaux_update,
)

__all__ = [
    'cartographie',
    'espaces_list',
    'campus_detail',
    'espace_detail',
    'espace_create',
    'espace_update',
    'espace_delete',
    'batiments_list',
    'batiment_detail',
    'batiment_create',
    'batiment_update',
    'batiment_delete',
    'batiment_import_sig',
    'terrains_list',
    'terrain_detail',
    'terrain_create',
    'terrain_update',
    'terrain_delete',
    'voiries_list',
    'voirie_detail',
    'voirie_create',
    'voirie_update',
    'voirie_delete',
    'espaces_verts_list',
    'espace_vert_detail',
    'espace_vert_create',
    'espace_vert_update',
    'espace_vert_delete',
    'suivi_travaux_list',
    'suivi_travaux_update',
]
