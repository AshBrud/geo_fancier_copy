from .models_campus import Campus, superficie_campus_totale
from .models_espace import Espace
from .models_batiment import FonctionBatiment, Batiment
from .models_terrain import Terrain
from .models_espace_vert import EspaceVert
from .models_voirie import Voirie, PointInteret
from .models_suivi_travaux import SuiviTravaux

__all__ = [
    'Campus',
    'superficie_campus_totale',
    'Espace',
    'FonctionBatiment',
    'Batiment',
    'Terrain',
    'EspaceVert',
    'Voirie',
    'PointInteret',
    'SuiviTravaux',
]
