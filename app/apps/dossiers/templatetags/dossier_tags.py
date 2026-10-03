"""
Balises et filtres de template pour GéoFoncier V2 (Contextual Terminology).

Permet la contextualisation dynamique du vocabulaire selon le Type d'espace :
Usage :
  {% load dossier_tags %}
  <h5>{{ active_dossier|term:'bati_plural' }}</h5>
  <span>{{ active_dossier|term:'occupant_label' }}</span>
"""

from django import template
from dossiers.services import get_term, get_dossier_lexicon

register = template.Library()


@register.filter(name='term')
def term_filter(dossier_or_type, term_args: str) -> str:
    """
    Filtre template retournant le terme contextuel pour ce dossier.
    Syntaxe :
      {{ active_dossier|term:'cle' }}
      {{ active_dossier|term:'cle,Valeur par défaut' }}
    """
    if not term_args:
        return ''

    parts = [p.strip() for p in str(term_args).split(',', 1)]
    term_key = parts[0]
    default_val = parts[1] if len(parts) > 1 else None

    return get_term(dossier_or_type, term_key, default=default_val)


@register.simple_tag(name='get_lexicon')
def get_lexicon_tag(dossier_or_type):
    """
    Tag simple retournant le dictionnaire complet des termes pour le dossier.
    Syntaxe :
      {% get_lexicon active_dossier as lexicon %}
      {{ lexicon.bati_plural }}
    """
    return get_dossier_lexicon(dossier_or_type)
