"""
Sélecteurs de données (queries en lecture seule) pour le module urbanisme.
Isole les requêtes complexes, filtres et calculs de bilans d'affichage.
"""
import json
from django.db.models import Q
from dossiers.models import ZoneSecteur
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction
from urbanisme.services.services_faisabilite import (
    calculer_superficie_allouee_espace,
    calculer_pks_pour_espace,
)


def get_projets_construction_qs(dossier=None, statut=None, search_term=None):
    """
    Retourne la liste filtrée des demandes de construction avec optimisation SQL.
    """
    qs = NouvelleConstruction.objects.select_related('demandeur', 'dossier', 'zone_secteur')
    if dossier:
        qs = qs.filter(dossier=dossier)
    if statut:
        qs = qs.filter(statut=statut)
    if search_term:
        qs = qs.filter(
            Q(nom_projet__icontains=search_term) |
            Q(type_construction__icontains=search_term)
        )
    return qs.order_by('-date_demande')


def get_projet_by_id(pk):
    """Retourne une demande de construction par son identifiant ou None."""
    try:
        return NouvelleConstruction.objects.select_related(
            'demandeur', 'dossier', 'zone_secteur'
        ).get(pk=pk)
    except NouvelleConstruction.DoesNotExist:
        return None


def get_constructions_recentes(dossier=None, limit=5):
    """Retourne les dernières demandes de constructions déposées."""
    qs = NouvelleConstruction.objects.select_related('demandeur', 'dossier')
    if dossier:
        qs = qs.filter(dossier=dossier)
    return qs.order_by('-date_demande')[:limit]


def get_historique_travaux_qs(annee=None, type_travaux=None, unite_batie=None):
    """
    Retourne la liste des chantiers et historiques d'interventions sur le bâti.
    """
    qs = HistoriqueConstruction.objects.select_related('unite_batie')
    if annee:
        qs = qs.filter(date_debut__year=annee)
    if type_travaux:
        qs = qs.filter(type_travaux=type_travaux)
    if unite_batie:
        qs = qs.filter(unite_batie=unite_batie)
    return qs.order_by('-date_debut')


def get_historique_annees_disponibles():
    """Retourne la liste distincte des années d'intervention."""
    return HistoriqueConstruction.objects.dates('date_debut', 'year', order='DESC')


def get_bilan_espace(zone_ou_espace, statuts=None, exclude_pk=None):
    """
    Calcule le bilan volumétrique et surfacique d'une zone ou espace foncier.
    """
    sup_brute = getattr(zone_ou_espace, 'superficie_m2', None) or getattr(zone_ou_espace, 'superficie', 0) or 0
    taux_occ = getattr(zone_ou_espace, 'taux_occupation', 40.0) or 40.0
    sup_constructible = sup_brute * (taux_occ / 100.0)

    sup_allouee = calculer_superficie_allouee_espace(
        zone_ou_espace, statuts=statuts, exclude_pk=exclude_pk
    )

    if hasattr(zone_ou_espace, 'unites_baties'):
        from django.db.models import Sum
        sup_batie = zone_ou_espace.unites_baties.aggregate(s=Sum('superficie_m2'))['s'] or 0.0
    else:
        sup_batie = getattr(zone_ou_espace, 'superficie_batie', 0.0) or 0.0

    sup_terrains = getattr(zone_ou_espace, 'superficie_terrains', 0.0) or 0.0
    sup_espaces_verts = getattr(zone_ou_espace, 'superficie_espaces_verts', 0.0) or 0.0
    sup_occupee = sup_allouee + sup_batie + sup_terrains + sup_espaces_verts
    sup_nette = max(0.0, sup_constructible - sup_occupee)
    pct = round(sup_occupee / sup_constructible * 100, 1) if sup_constructible else 0.0

    return {
        'brute': sup_brute,
        'constructible': sup_constructible,
        'batie': sup_batie,
        'terrains': sup_terrains,
        'espaces_verts': sup_espaces_verts,
        'allouee': sup_allouee,
        'occupee': sup_occupee,
        'nette': sup_nette,
        'pct': pct,
    }


def get_espaces_constructibles_data(dossier=None):
    """
    Prépare et sérialise la liste des zones constructibles avec leur bilan
    pour l'injection dans les interfaces cartographiques Leaflet/OpenLayers.
    """
    qs = ZoneSecteur.objects.filter(
        type_zone__in=[
            ZoneSecteur.TYPE_ESPACE_LIBRE,
            ZoneSecteur.TYPE_SECTEUR_CAMPUS,
            ZoneSecteur.TYPE_ZONE_ACTIVITE,
            ZoneSecteur.TYPE_VILLAGE,
            ZoneSecteur.TYPE_QUARTIER,
        ]
    )
    if dossier:
        qs = qs.filter(dossier=dossier)
    qs = qs.order_by('nom')

    espaces_data = []
    for z in qs:
        if z.geometrie:
            bilan = get_bilan_espace(z)
            espaces_data.append({
                'id': z.pk,
                'nom': z.nom,
                'code': z.code,
                'superficie': z.superficie_m2 or 0,
                'taux_occupation': getattr(z, 'taux_occupation', 40),
                'sup_constructible': bilan['constructible'],
                'sup_engagee': bilan['allouee'],
                'sup_batie': bilan['batie'],
                'sup_disponible': bilan['nette'],
                'geojson': json.loads(z.geometrie.geojson),
            })
    return espaces_data
