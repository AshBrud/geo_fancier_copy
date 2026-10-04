"""
Services métier pour les signalements d'incidents (SignalementDommage).
Architecture GeenkoDev : mutations, transitions d'état et validation.
"""

from typing import Dict, Any, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry, Point
from dossiers.models import SignalementDommage, Dossier, ZoneSecteur


def to_point(geom) -> Optional[Point]:
    """Valide et convertit en Point WGS 84."""
    if not geom:
        return None
    if isinstance(geom, str):
        try:
            geom = GEOSGeometry(geom)
        except Exception as e:
            raise ValidationError(f"Point GPS invalide : {e}")
    if isinstance(geom, Point):
        geom.srid = 4326
        return geom
    raise ValidationError("La localisation doit être un Point géographique.")


@transaction.atomic
def creer_signalement(
    dossier: Dossier,
    data: Dict[str, Any],
    auteur: Optional[Any] = None,
) -> SignalementDommage:
    """Crée un signalement géolocalisé pour le dossier territorial."""
    point = to_point(data.get('geometrie'))
    if not point:
        raise ValidationError("Le point géographique d'incident est requis.")

    zone_id = data.get('zone_secteur')
    zone = None
    if zone_id:
        zone = zone_id if isinstance(zone_id, ZoneSecteur) else ZoneSecteur.objects.filter(dossier=dossier, pk=zone_id).first()

    sig = SignalementDommage(
        dossier=dossier,
        zone_secteur=zone,
        titre=data.get('titre', '').strip(),
        categorie=data.get('categorie', SignalementDommage.CAT_AUTRE),
        priorite=data.get('priorite', SignalementDommage.PRIORITE_NORMALE),
        statut=SignalementDommage.STATUT_NOUVEAU,
        description=data.get('description', '').strip(),
        geometrie=point,
        photo=data.get('photo'),
        auteur=auteur,
    )
    sig.full_clean()
    sig.save()
    return sig


@transaction.atomic
def modifier_statut_signalement(
    signalement: SignalementDommage,
    nouveau_statut: str,
    commentaire: str = '',
    user: Optional[Any] = None,
) -> SignalementDommage:
    """Fait progresser le statut d'un signalement."""
    statuts_valides = dict(SignalementDommage.STATUTS)
    if nouveau_statut not in statuts_valides:
        raise ValidationError(f"Statut inconnu : {nouveau_statut}")

    signalement.statut = nouveau_statut
    if nouveau_statut == SignalementDommage.STATUT_RESOLU:
        signalement.date_resolution = timezone.now()
        signalement.commentaire_resolution = commentaire.strip()
    elif commentaire:
        if signalement.commentaire_resolution:
            signalement.commentaire_resolution += f"\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] {commentaire.strip()}"
        else:
            signalement.commentaire_resolution = f"[{timezone.now().strftime('%d/%m/%Y %H:%M')}] {commentaire.strip()}"

    signalement.save()
    return signalement


@transaction.atomic
def supprimer_signalement(signalement: SignalementDommage, user: Optional[Any] = None) -> Tuple[int, Dict[str, int]]:
    """Supprime un signalement."""
    return signalement.delete()
