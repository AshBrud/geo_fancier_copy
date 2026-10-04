from .views_media import (
    capture_photo,
    flux_video_delete,
    flux_video_import,
    flux_videos_list,
    photo_drone_delete,
    photos_drone_list,
)
from .views_mission import (
    mission_create,
    mission_delete,
    mission_detail,
    mission_list,
    mission_marquer_traitement,
    mission_photos_import,
    mission_update,
)
from .views_orthophoto import (
    import_orthophoto,
    orthophoto_delete,
    orthophoto_integrate,
    orthophoto_validate,
)
from .views_supervision import (
    flux_diffuser_start,
    flux_diffuser_stop,
    flux_start,
    flux_stop,
    perspectives,
    supervision_donnees,
)

__all__ = [
    'mission_list',
    'mission_create',
    'mission_detail',
    'mission_update',
    'mission_delete',
    'mission_marquer_traitement',
    'mission_photos_import',
    'import_orthophoto',
    'orthophoto_delete',
    'orthophoto_validate',
    'orthophoto_integrate',
    'perspectives',
    'supervision_donnees',
    'flux_start',
    'flux_stop',
    'flux_diffuser_start',
    'flux_diffuser_stop',
    'flux_videos_list',
    'flux_video_import',
    'flux_video_delete',
    'capture_photo',
    'photos_drone_list',
    'photo_drone_delete',
]
