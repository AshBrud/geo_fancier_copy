"""
Service de résolution sémantique et lexicale pour GéoFoncier V2 (Contextual Terminology).

Permet d'adapter dynamiquement les libellés de l'interface en fonction du Type d'espace
associé au dossier territorial actif.
"""

from typing import Any, Dict, Optional
from dossiers.constants import TERMINOLOGY_CATALOG, DEFAULT_TERMS


def resolve_space_type(dossier_or_type: Any) -> str:
    """
    Extrait la chaîne identifiant le Type d'espace à partir d'un objet Dossier
    ou d'une chaîne brute.
    """
    if not dossier_or_type:
        return 'autre'

    if isinstance(dossier_or_type, str):
        return dossier_or_type.strip().lower()

    # Si c'est un objet Dossier ou équivalent
    return getattr(dossier_or_type, 'type_territoire', None) or getattr(dossier_or_type, 'type_espace', 'autre')


def get_term(dossier_or_type: Any, term_key: str, default: Optional[str] = None) -> str:
    """
    Retourne le terme contextualisé correspondant à la clé demandée pour ce dossier.
    Exemples de clés : 'sol_label', 'sol_plural', 'bati_label', 'bati_plural', 'occupant_label'...
    """
    space_type = resolve_space_type(dossier_or_type)
    lexicon = TERMINOLOGY_CATALOG.get(space_type, TERMINOLOGY_CATALOG.get('autre', DEFAULT_TERMS))

    if term_key in lexicon:
        return lexicon[term_key]

    if default is not None:
        return default

    return DEFAULT_TERMS.get(term_key, term_key.replace('_', ' ').capitalize())


def get_dossier_lexicon(dossier_or_type: Any) -> Dict[str, str]:
    """
    Retourne l'intégralité du lexique contextuel applicable pour un dossier.
    Utile pour l'injection dans les context processors ou les payloads JSON.
    """
    space_type = resolve_space_type(dossier_or_type)
    lexicon = TERMINOLOGY_CATALOG.get(space_type, TERMINOLOGY_CATALOG.get('autre', DEFAULT_TERMS)).copy()
    lexicon['space_type'] = space_type
    return lexicon
