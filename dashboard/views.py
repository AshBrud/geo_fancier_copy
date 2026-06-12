from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from foncier.models import Espace, Batiment
from drones.models import MissionDrone, Orthophoto
from constructions.models import NouvelleConstruction, HistoriqueConstruction
from accounts.models import CustomUser, ActivityLog
import json


@login_required
def index(request):
    # KPIs fonciers
    # Superficie totale du campus : valeur officielle (55 ha)
    superficie_totale = 550000  # m² — 55 hectares exacts
    superficie_occupee = Espace.objects.filter(
        type_espace=Espace.TYPE_OCCUPE).aggregate(t=Sum('superficie'))['t'] or 0
    superficie_libre = Espace.objects.filter(
        type_espace=Espace.TYPE_LIBRE).aggregate(t=Sum('superficie'))['t'] or 0
    superficie_reservee = Espace.objects.filter(
        type_espace=Espace.TYPE_RESERVE).aggregate(t=Sum('superficie'))['t'] or 0
    taux_occupation = round((superficie_occupee / superficie_totale * 100) if superficie_totale else 0, 1)

    total_batiments = Batiment.objects.filter(est_actif=True).count()
    total_missions  = MissionDrone.objects.count()
    total_constructions = NouvelleConstruction.objects.count()

    nb_espaces_libres  = Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count()
    missions_traitees  = MissionDrone.objects.filter(statut='traite').count()
    missions_planifiees = MissionDrone.objects.filter(statut='planifie').count()
    constructions_attente  = NouvelleConstruction.objects.filter(statut='attente').count()
    constructions_approuvees = NouvelleConstruction.objects.filter(statut='approuvee').count()

    # Données pour graphique répartition des espaces
    types_data = Espace.objects.values('type_espace').annotate(
        superficie=Sum('superficie'), count=Count('id')
    )
    chart_labels = [Espace.COULEURS.get(t['type_espace'], '#ccc') for t in types_data]
    chart_data = []
    chart_names = []
    for t in types_data:
        display = dict(Espace.TYPES).get(t['type_espace'], t['type_espace'])
        chart_names.append(display)
        chart_data.append(round((t['superficie'] or 0) / 10000, 2))

    # Évolution constructions par année
    from django.db.models.functions import ExtractYear
    histo_annees = (
        HistoriqueConstruction.objects
        .annotate(annee=ExtractYear('date_debut'))
        .values('annee')
        .annotate(count=Count('id'))
        .order_by('annee')
    )
    evol_labels = [str(h['annee']) for h in histo_annees]
    evol_data = [h['count'] for h in histo_annees]

    # Activités récentes — journal complet réservé à l'admin
    activites = None
    if request.user.is_admin:
        activites = ActivityLog.objects.select_related('user').all()[:8]

    # Résumé d'activités pour les utilisateurs non-admin
    batiments_recents = Batiment.objects.order_by('-date_ajout')[:4]
    missions_recentes = MissionDrone.objects.order_by('-date_creation')[:4]
    constructions_recentes = NouvelleConstruction.objects.select_related(
        'demandeur').order_by('-date_demande')[:5]

    context = {
        'superficie_totale': round(superficie_totale / 10000, 2),
        'superficie_occupee': round(superficie_occupee / 10000, 2),
        'superficie_libre': round(superficie_libre / 10000, 2),
        'superficie_reservee': round(superficie_reservee / 10000, 2),
        'taux_occupation': taux_occupation,
        'total_batiments': total_batiments,
        'total_missions': total_missions,
        'total_constructions': total_constructions,
        'total_espaces': Espace.objects.count(),
        'chart_labels': json.dumps(chart_names),
        'chart_data': json.dumps(chart_data),
        'chart_colors': json.dumps(chart_labels),
        'evol_labels': json.dumps(evol_labels),
        'evol_data': json.dumps(evol_data),
        'activites': activites,
        'batiments_recents': batiments_recents,
        'missions_recentes': missions_recentes,
        'constructions_recentes': constructions_recentes,
        'nb_espaces_libres': nb_espaces_libres,
        'missions_traitees': missions_traitees,
        'missions_planifiees': missions_planifiees,
        'constructions_attente': constructions_attente,
        'constructions_approuvees': constructions_approuvees,
    }
    return render(request, 'dashboard/index.html', context)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('accounts:login')
