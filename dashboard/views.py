from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from foncier.models import Espace, Batiment, SUPERFICIE_CAMPUS_M2
from drones.models import Orthophoto, Mission
from constructions.models import NouvelleConstruction, HistoriqueConstruction
from accounts.models import CustomUser, ActivityLog
import json


@login_required
def index(request):
    # KPIs fonciers
    superficie_totale = SUPERFICIE_CAMPUS_M2  # superficie officielle campus UAD
    superficie_occupee = Espace.objects.filter(
        type_espace=Espace.TYPE_OCCUPE).aggregate(t=Sum('superficie'))['t'] or 0
    superficie_reservee = Espace.objects.filter(
        type_espace=Espace.TYPE_RESERVE).aggregate(t=Sum('superficie'))['t'] or 0
    def _sup_statut(statut):
        return NouvelleConstruction.objects.filter(
            statut=statut
        ).aggregate(t=Sum('superficie_souhaitee'))['t'] or 0

    sup_approuvee  = _sup_statut(NouvelleConstruction.STATUT_APPROUVE)
    sup_en_cours   = _sup_statut(NouvelleConstruction.STATUT_EN_COURS)
    sup_allouee    = sup_approuvee + sup_en_cours
    # Superficie libre = superficie totale officielle − superficie réellement utilisée
    superficie_libre = max(0, superficie_totale - superficie_occupee - superficie_reservee - sup_allouee)
    superficie_prise = superficie_occupee + sup_allouee
    taux_occupation = round((superficie_prise / superficie_totale * 100) if superficie_totale else 0, 1)

    total_batiments = Batiment.objects.filter(est_actif=True).count()
    total_orthophotos = Orthophoto.objects.count()
    total_constructions = NouvelleConstruction.objects.count()
    total_missions = Mission.objects.count()
    missions_integrees = Mission.objects.filter(statut=Mission.STATUT_INTEGREE).count()

    nb_espaces_libres  = Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count()
    constructions_en_cours   = NouvelleConstruction.objects.filter(statut='en_cours').count()
    constructions_approuvees = NouvelleConstruction.objects.filter(statut='approuvee').count()

    # ── Bilan de la capacité constructible de l'université ──
    espaces_actifs = list(Espace.objects.filter(
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE]
    ))
    sup_constructible_totale = sum(
        (e.superficie or 0) * (e.taux_occupation / 100)
        for e in espaces_actifs
    )

    sup_constr_nette = max(0.0, sup_constructible_totale - sup_allouee)

    def _pct(val, total):
        return round(val / total * 100, 1) if total else 0

    pct_alloue    = _pct(sup_allouee,   sup_constructible_totale)
    pct_approuvee = _pct(sup_approuvee, sup_constructible_totale)
    pct_en_cours  = _pct(sup_en_cours,  sup_constructible_totale)
    nb_engagees   = NouvelleConstruction.objects.filter(
        statut__in=NouvelleConstruction.STATUTS_ENGAGES
    ).count()

    # Données pour graphique répartition des espaces
    chart_names = ['Espace libre', 'Espace occupé / alloué', 'Espace réservé']
    chart_labels = [
        Espace.COULEURS.get(Espace.TYPE_LIBRE, '#16A34A'),
        Espace.COULEURS.get(Espace.TYPE_OCCUPE, '#DC2626'),
        Espace.COULEURS.get(Espace.TYPE_RESERVE, '#F59E0B'),
    ]
    chart_data = [
        round(superficie_libre / 10000, 2),
        round(superficie_prise / 10000, 2),
        round(superficie_reservee / 10000, 2),
    ]

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
    orthophotos_recentes = Orthophoto.objects.order_by('-date_ajout')[:4]
    constructions_recentes = NouvelleConstruction.objects.select_related(
        'demandeur').order_by('-date_demande')[:5]

    context = {
        'superficie_totale': round(superficie_totale / 10000, 2),
        'superficie_occupee': round(superficie_prise / 10000, 2),
        'superficie_libre': round(superficie_libre / 10000, 2),
        'superficie_reservee': round(superficie_reservee / 10000, 2),
        'taux_occupation': taux_occupation,
        'total_batiments': total_batiments,
        'total_orthophotos': total_orthophotos,
        'total_constructions': total_constructions,
        'total_missions': total_missions,
        'missions_integrees': missions_integrees,
        'total_espaces': Espace.objects.count(),
        'chart_labels': json.dumps(chart_names),
        'chart_data': json.dumps(chart_data),
        'chart_colors': json.dumps(chart_labels),
        'evol_labels': json.dumps(evol_labels),
        'evol_data': json.dumps(evol_data),
        'activites': activites,
        'batiments_recents': batiments_recents,
        'orthophotos_recentes': orthophotos_recentes,
        'constructions_recentes': constructions_recentes,
        'nb_espaces_libres': nb_espaces_libres,
        'constructions_en_cours': constructions_en_cours,
        'constructions_approuvees': constructions_approuvees,
        # Capacité constructible
        'sup_constructible_totale':    round(sup_constructible_totale),
        'sup_constructible_totale_ha': round(sup_constructible_totale / 10000, 2),
        'sup_allouee':    round(sup_allouee),
        'sup_allouee_ha': round(sup_allouee / 10000, 2),
        'sup_approuvee':  round(sup_approuvee),
        'sup_en_cours':   round(sup_en_cours),
        'sup_constr_nette':    round(sup_constr_nette),
        'sup_constr_nette_ha': round(sup_constr_nette / 10000, 2),
        'pct_alloue':    pct_alloue,
        'pct_approuvee': pct_approuvee,
        'pct_en_cours':  pct_en_cours,
        'nb_engagees':   nb_engagees,
    }
    return render(request, 'dashboard/index.html', context)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('accounts:login')
