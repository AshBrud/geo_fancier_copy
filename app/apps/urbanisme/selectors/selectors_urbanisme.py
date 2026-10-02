"""
Sélecteurs de données (queries en lecture seule) pour le module urbanisme.
Isole les requêtes complexes, filtres et calculs de bilans d'affichage.
"""
import json
from django.db.models import Q
from territoire.models import Espace
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction
from urbanisme.services.services_faisabilite import (
    calculer_superficie_allouee_espace,
    calculer_pks_pour_espace,
)


def get_projets_construction_qs(dossier=None, statut=None, search_term=None):
    """
    Retourne la liste filtrée des demandes de construction avec optimisation SQL.
    """
    qs = NouvelleConstruction.objects.select_related('demandeur', 'dossier', 'zone_secteur', 'espace_souhaitee')
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
            'demandeur', 'dossier', 'zone_secteur', 'espace_souhaitee'
        ).get(pk=pk)
    except NouvelleConstruction.DoesNotExist:
        return None


def get_constructions_recentes(dossier=None, limit=5):
    """Retourne les dernières demandes de constructions déposées."""
    qs = NouvelleConstruction.objects.select_related('demandeur', 'dossier')
    if dossier:
        qs = qs.filter(dossier=dossier)
    return qs.order_by('-date_demande')[:limit]


def get_historique_travaux_qs(annee=None, type_travaux=None, batiment=None, unite_batie=None):
    """
    Retourne la liste des chantiers et historiques d'interventions sur le bâti.
    """
    qs = HistoriqueConstruction.objects.select_related('batiment', 'unite_batie')
    if annee:
        qs = qs.filter(date_debut__year=annee)
    if type_travaux:
        qs = qs.filter(type_travaux=type_travaux)
    if batiment:
        qs = qs.filter(batiment=batiment)
    if unite_batie:
        qs = qs.filter(unite_batie=unite_batie)
    return qs.order_by('-date_debut')


def get_historique_annees_disponibles():
    """Retourne la liste distincte des années d'intervention."""
    return HistoriqueConstruction.objects.dates('date_debut', 'year', order='DESC')


def get_bilan_espace(espace, statuts=None, exclude_pk=None):
    """
    Calcule le bilan volumétrique et surfacique d'un espace foncier.
    """
    sup_brute = espace.superficie or 0
    sup_constructible = (
        sup_brute * (espace.taux_occupation / 100)
        if espace.type_espace in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE)
        else 0.0
    )
    sup_allouee = calculer_superficie_allouee_espace(
        espace, statuts=statuts, exclude_pk=exclude_pk
    )
    sup_batie = espace.superficie_batie
    sup_terrains = espace.superficie_terrains
    sup_espaces_verts = espace.superficie_espaces_verts
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


def get_espaces_constructibles_data():
    """
    Prépare et sérialise la liste des espaces libres et constructibles avec leur bilan
    pour l'injection dans les interfaces cartographiques Leaflet/OpenLayers.
    """
    espaces_libres = Espace.objects.filter(
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE]
    ).order_by('nom')

    espaces_data = []
    for e in espaces_libres:
        if e.geometrie:
            bilan = get_bilan_espace(e)
            espaces_data.append({
                'id': e.pk,
                'nom': e.nom,
                'code': e.code,
                'superficie': e.superficie or 0,
                'taux_occupation': e.taux_occupation,
                'sup_constructible': bilan['constructible'],
                'sup_engagee': bilan['allouee'],
                'sup_batie': bilan['batie'],
                'sup_disponible': bilan['nette'],
                'geojson': json.loads(e.geometrie.geojson),
            })
    return espaces_data
