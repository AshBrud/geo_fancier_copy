"""
Services métier pour les subdivisions territoriales (ZoneSecteur).
Architecture GeenkoDev : logique métier, transactions, validation et mutations.
"""

from typing import Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from dossiers.models import ZoneSecteur, Dossier


def to_multipolygon(geom) -> Optional[MultiPolygon]:
    """Assure qu'une géométrie polygonale est encapsulée en MultiPolygon WGS 84."""
    if not geom:
        return None
    if isinstance(geom, str):
        try:
            geom = GEOSGeometry(geom)
        except Exception as e:
            raise ValidationError(f"Format de géométrie invalide : {e}")

    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=geom.srid or 4326)
    raise ValidationError("La géométrie doit être un polygone ou un multi-polygone.")


@transaction.atomic
def creer_zone_secteur(
    dossier: Dossier,
    nom: str,
    geometrie: Any,
    type_zone: str = ZoneSecteur.TYPE_SECTEUR_CAMPUS,
    code: str = '',
    description: str = '',
    responsable_nom: str = '',
    responsable_telephone: str = '',
    population_estimee: Optional[int] = None,
    metadata_specifique: Optional[Dict[str, Any]] = None,
) -> ZoneSecteur:
    """Crée une nouvelle subdivision territoriale avec calcul automatique des surfaces et SRID."""
    if not dossier:
        raise ValidationError("Un dossier de rattachement est obligatoire.")

    multi_geom = to_multipolygon(geometrie)

    zone = ZoneSecteur(
        dossier=dossier,
        code=code.strip(),
        nom=nom.strip(),
        type_zone=type_zone,
        geometrie=multi_geom,
        description=description.strip(),
        responsable_nom=responsable_nom.strip(),
        responsable_telephone=responsable_telephone.strip(),
        population_estimee=population_estimee,
        metadata_specifique=metadata_specifique or {},
    )
    zone.full_clean()
    zone.save()
    return zone


@transaction.atomic
def modifier_zone_secteur(
    zone: ZoneSecteur,
    **champs_a_mettre_a_jour,
) -> ZoneSecteur:
    """Met à jour les attributs ou la géométrie d'une subdivision territoriale."""
    if 'geometrie' in champs_a_mettre_a_jour and champs_a_mettre_a_jour['geometrie']:
        champs_a_mettre_a_jour['geometrie'] = to_multipolygon(champs_a_mettre_a_jour['geometrie'])

    for champ, valeur in champs_a_mettre_a_jour.items():
        if hasattr(zone, champ):
            setattr(zone, champ, valeur)

    zone.full_clean()
    zone.save()
    return zone


@transaction.atomic
def supprimer_zone_secteur(zone: ZoneSecteur) -> bool:
    """Supprime une subdivision territoriale."""
    zone.delete()
    return True
