def notifications(request):
    """Cloche de la barre supérieure : notifications non lues de l'utilisateur."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    non_lues = user.notifications_commune.filter(lue=False)
    return {
        'notif_non_lues': non_lues.count(),
        'notif_recentes': user.notifications_commune.select_related('signalement')[:6],
    }
