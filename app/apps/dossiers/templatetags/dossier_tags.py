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
def term_filter(value, arg=None) -> str:
    """
    Filtre template retournant le terme contextuel pour ce dossier.
    Supporte les deux syntaxes :
      1. Syntaxe standard : {{ active_dossier|term:'zone_plural' }}
      2. Syntaxe inversée : {{ 'espace_label'|term }}
    """
    if not value:
        return ''

    if arg is not None:
        parts = [p.strip() for p in str(arg).split(',', 1)]
        term_key = parts[0]
        default_val = parts[1] if len(parts) > 1 else None
        return get_term(value, term_key, default=default_val)
    else:
        parts = [p.strip() for p in str(value).split(',', 1)]
        term_key = parts[0]
        default_val = parts[1] if len(parts) > 1 else None
        return get_term(None, term_key, default=default_val)


@register.simple_tag(name='get_lexicon')
def get_lexicon_tag(dossier_or_type):
    """
    Tag simple retournant le dictionnaire complet des termes pour le dossier.
    Syntaxe :
      {% get_lexicon active_dossier as lexicon %}
      {{ lexicon.bati_plural }}
    """
    return get_dossier_lexicon(dossier_or_type)


@register.simple_tag(takes_context=True, name='ws_url')
def ws_url(context, view_name, *args, **kwargs):
    """
    Génère l'URL préfixée par le slug du dossier actif si l'utilisateur est dans un espace territorial.
    Exemple : 
      {% ws_url 'drones:missions' %} -> /{slug}/drones/
      {% ws_url 'drones:perspectives' %} -> /{slug}/drones/perspectives/
      {% ws_url 'drones:flux_videos' %} -> /{slug}/drones/flux/videos/
      {% ws_url 'drones:mission_detail' mission.pk %} -> /{slug}/drones/missions/5/
    """
    from django.urls import reverse
    url = reverse(view_name, args=args, kwargs=kwargs)
    active_dossier = context.get('active_dossier')
    if active_dossier and getattr(active_dossier, 'slug', None):
        slug = active_dossier.slug
        if not url.startswith(f'/{slug}/'):
            url = f'/{slug}{url}'
    return url

