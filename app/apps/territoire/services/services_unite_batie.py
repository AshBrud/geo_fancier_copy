"""
Services métier pour le recensement bâti unifié (UniteBatie).
Architecture GeenkoDev : mutations, transactions, validation et imports SIG.
"""

import json
from typing import Dict, Any, Optional, Tuple, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from dossiers.models import UniteBatie, Dossier, ZoneSecteur


def to_multipolygon(geom) -> Optional[MultiPolygon]:
    """Encapsule une géométrie polygonale en MultiPolygon WGS 84."""
    if not geom:
        return None
    if isinstance(geom, str):
        try:
            geom = GEOSGeometry(geom)
        except Exception as e:
            raise ValidationError(f"Format de géométrie invalide : {e}")
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=4326)
    if isinstance(geom, MultiPolygon):
        geom.srid = 4326
        return geom
    raise ValidationError("La géométrie doit être un polygone ou multipolygone.")


@transaction.atomic
def creer_unite_batie(
    dossier: Dossier,
    data: Dict[str, Any],
    user: Optional[Any] = None,
) -> UniteBatie:
    """Crée une unité bâtie rattachée à un workspace territorial."""
    geom = to_multipolygon(data.get('geometrie'))
    if not geom:
        raise ValidationError("L'emprise spatiale du bâtiment est requise.")

    zone_id = data.get('zone_secteur')
    zone = None
    if zone_id:
        if isinstance(zone_id, ZoneSecteur):
            zone = zone_id
        else:
            zone = ZoneSecteur.objects.filter(dossier=dossier, pk=zone_id).first()

    unite = UniteBatie(
        dossier=dossier,
        zone_secteur=zone,
        code=data.get('code', '').strip(),
        nom=data.get('nom', '').strip(),
        type_bati=data.get('type_bati', UniteBatie.TYPE_HABITATION),
        statut_occupation=data.get('statut_occupation', UniteBatie.OCCUPATION_HABITEE),
        etages=data.get('etages', 1) or 1,
        annee_construction=data.get('annee_construction'),
        geometrie=geom,
        photo=data.get('photo'),
        est_actif=data.get('est_actif', True),
        description=data.get('description', '').strip(),
        metadata_specifique=data.get('metadata_specifique') or {},
    )
    unite.full_clean()
    unite.save()
    return unite


@transaction.atomic
def modifier_unite_batie(
    unite: UniteBatie,
    data: Dict[str, Any],
    user: Optional[Any] = None,
) -> UniteBatie:
    """Met à jour les attributs et l'emprise d'une unité bâtie."""
    if 'nom' in data:
        unite.nom = data['nom'].strip()
    if 'code' in data and data['code']:
        unite.code = data['code'].strip()
    if 'type_bati' in data:
        unite.type_bati = data['type_bati']
    if 'statut_occupation' in data:
        unite.statut_occupation = data['statut_occupation']
    if 'etages' in data:
        unite.etages = data['etages'] or 1
    if 'annee_construction' in data:
        unite.annee_construction = data['annee_construction']
    if 'photo' in data and data['photo']:
        unite.photo = data['photo']
    if 'est_actif' in data:
        unite.est_actif = bool(data['est_actif'])
    if 'description' in data:
        unite.description = data['description'].strip()
    if 'zone_secteur' in data:
        z = data['zone_secteur']
        unite.zone_secteur = z if isinstance(z, ZoneSecteur) else ZoneSecteur.objects.filter(dossier=unite.dossier, pk=z).first()
    if 'geometrie' in data and data['geometrie']:
        unite.geometrie = to_multipolygon(data['geometrie'])

    unite.full_clean()
    unite.save()
    return unite


@transaction.atomic
def supprimer_unite_batie(unite: UniteBatie, user: Optional[Any] = None) -> Tuple[int, Dict[str, int]]:
    """Supprime une unité bâtie."""
    return unite.delete()


@transaction.atomic
def importer_unites_baties_geojson(
    dossier: Dossier,
    geojson_raw: str,
    user: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Importe en masse des unités bâties depuis un fichier GeoJSON FeatureCollection.
    Crée les entités et associe automatiquement la zone si le centroïde est inclus.
    """
    data = json.loads(geojson_raw)
    features = data.get('features', [])
    created = 0
    errors = []

    zones = list(ZoneSecteur.objects.filter(dossier=dossier))

    for idx, feat in enumerate(features):
        try:
            geom_dict = feat.get('geometry')
            if not geom_dict:
                continue
            geom = GEOSGeometry(json.dumps(geom_dict))
            mp = to_multipolygon(geom)
            props = feat.get('properties', {})

            nom = props.get('nom') or props.get('name') or props.get('designation') or ''
            code = props.get('code') or props.get('id') or ''

            # Détection de zone par intersection spatiale
            zone_associee = None
            for z in zones:
                if z.geometrie and (z.geometrie.contains(mp.centroid) or z.geometrie.intersects(mp)):
                    zone_associee = z
                    break

            bat = UniteBatie(
                dossier=dossier,
                zone_secteur=zone_associee,
                code=str(code) if code else '',
                nom=str(nom),
                type_bati=props.get('type_bati', UniteBatie.TYPE_HABITATION),
                statut_occupation=props.get('statut_occupation', UniteBatie.OCCUPATION_HABITEE),
                etages=int(props.get('etages', 1) or 1),
                geometrie=mp,
                description=props.get('description', ''),
                metadata_specifique=props,
            )
            bat.save()
            created += 1
        except Exception as e:
            errors.append(f"Feature #{idx}: {e}")

    return {
        'total_features': len(features),
        'created': created,
        'errors': errors,
    }
