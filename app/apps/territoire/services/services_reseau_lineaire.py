"""
Services métier pour les réseaux linéaires et voiries (ReseauLineaire).
Architecture GeenkoDev : mutations, transactions et conversions géométriques.
"""

from typing import Dict, Any, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry, MultiLineString, LineString
from dossiers.models import ReseauLineaire, Dossier


def to_multilinestring(geom) -> Optional[MultiLineString]:
    """Encapsule une géométrie linéaire en MultiLineString WGS 84."""
    if not geom:
        return None
    if isinstance(geom, str):
        try:
            geom = GEOSGeometry(geom)
        except Exception as e:
            raise ValidationError(f"Format de géométrie invalide : {e}")
    if isinstance(geom, LineString):
        return MultiLineString(geom, srid=4326)
    if isinstance(geom, MultiLineString):
        geom.srid = 4326
        return geom
    raise ValidationError("La géométrie doit être un tracé linéaire (LineString ou MultiLineString).")


@transaction.atomic
def creer_reseau_lineaire(
    dossier: Dossier,
    data: Dict[str, Any],
    user: Optional[Any] = None,
) -> ReseauLineaire:
    """Crée un tronçon linéaire rattaché au dossier territorial."""
    geom = to_multilinestring(data.get('geometrie'))
    if not geom:
        raise ValidationError("Le tracé géographique de la voie est obligatoire.")

    reseau = ReseauLineaire(
        dossier=dossier,
        code=data.get('code', '').strip(),
        nom=data.get('nom', '').strip(),
        type_voie=data.get('type_voie', ReseauLineaire.TYPE_PISTE),
        geometrie=geom,
        largeur_estimee_m=data.get('largeur_estimee_m'),
        etat_chaussee=data.get('etat_chaussee', '').strip(),
        description=data.get('description', '').strip(),
    )
    reseau.full_clean()
    reseau.save()
    return reseau


@transaction.atomic
def modifier_reseau_lineaire(
    reseau: ReseauLineaire,
    data: Dict[str, Any],
    user: Optional[Any] = None,
) -> ReseauLineaire:
    """Met à jour un tronçon linéaire."""
    if 'nom' in data:
        reseau.nom = data['nom'].strip()
    if 'code' in data and data['code']:
        reseau.code = data['code'].strip()
    if 'type_voie' in data:
        reseau.type_voie = data['type_voie']
    if 'largeur_estimee_m' in data:
        reseau.largeur_estimee_m = data['largeur_estimee_m']
    if 'etat_chaussee' in data:
        reseau.etat_chaussee = data['etat_chaussee'].strip()
    if 'description' in data:
        reseau.description = data['description'].strip()
    if 'geometrie' in data and data['geometrie']:
        reseau.geometrie = to_multilinestring(data['geometrie'])

    reseau.full_clean()
    reseau.save()
    return reseau


@transaction.atomic
def supprimer_reseau_lineaire(reseau: ReseauLineaire, user: Optional[Any] = None) -> Tuple[int, Dict[str, int]]:
    """Supprime un tronçon linéaire."""
    return reseau.delete()
