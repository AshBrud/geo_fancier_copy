from django import template

register = template.Library()


@register.filter(name='has_permission')
def has_permission(user, perm_code):
    """
    Filtre d'habilitation pour les templates Django (Défense en profondeur Niveau 3).
    Usage : {% if request.user|has_permission:'cadastre:create' %} ... {% endif %}
    """
    if not user or not user.is_authenticated:
        return False
    return user.has_perm_code(perm_code)


@register.simple_tag(name='user_can')
def user_can(user, perm_code):
    """
    Tag d'habilitation pour assignation conditionnelle ou affichage.
    Usage : {% user_can request.user 'drones:upload_photos' as can_upload %}
    """
    if not user or not user.is_authenticated:
        return False
    return user.has_perm_code(perm_code)
