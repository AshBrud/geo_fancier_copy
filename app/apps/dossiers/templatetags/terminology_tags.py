"""
Alias rétrocompatible pour terminology_tags réexportant dossier_tags.
Permet d'utiliser indistinctement {% load dossier_tags %} ou {% load terminology_tags %}.
"""

from .dossier_tags import register, term_filter, get_lexicon_tag

__all__ = ['register', 'term_filter', 'get_lexicon_tag']
