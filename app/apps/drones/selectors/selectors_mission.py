from django.db.models import Q
from django.shortcuts import get_object_or_404

from ..models import Mission, Orthophoto


def get_missions_queryset(q=None, statut=None, dossier=None):
    """Queryset filtrable pour les missions drone."""
    qs = Mission.objects.all()
    if dossier:
        qs = qs.filter(dossier=dossier)
    if q:
        qs = qs.filter(
            Q(nom__icontains=q)
            | Q(operateur__icontains=q)
            | Q(drone_utilise__icontains=q)
            | Q(notes__icontains=q)
        )
    if statut:
        qs = qs.filter(statut=statut)
    return qs.order_by('-date_vol')


def get_mission_by_id(pk):
    """Récupère une mission par son identifiant."""
    return get_object_or_404(Mission, pk=pk)


def get_mission_kpis(dossier=None):
    """Calcul des indicateurs clés (KPIs) de production drone."""
    missions_qs = Mission.objects.all()
    orthos_qs = Orthophoto.objects.all()
    if dossier:
        missions_qs = missions_qs.filter(dossier=dossier)
        orthos_qs = orthos_qs.filter(dossier=dossier)

    nb_missions = missions_qs.count()
    total_orthophotos = orthos_qs.count()
    nb_validees = orthos_qs.filter(valide=True).count()

    # Calcul de la surface cumulée des emprises valides
    surface_totale = 0.0
    for o in orthos_qs:
        s = o.superficie_ha
        if s:
            surface_totale += s

    return {
        'nb_missions': nb_missions,
        'total_orthophotos': total_orthophotos,
        'nb_validees': nb_validees,
        'surface_ha': round(surface_totale, 2),
    }
