from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from territoire.models import Espace, Batiment, Campus, Terrain, EspaceVert, Voirie
from drones.models import Orthophoto, Mission
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction
from accounts.models import CustomUser, ActivityLog
from habitations.views import _json_script
from habitations.models import Commune, Maison, OrthophotoCommune, Piste, Signalement, Village
from django.contrib import messages
from dossiers.selectors import get_dossier_by_slug, get_accessible_dossiers_for_user
import json


@login_required
def dashboard_router(request):
    """
    Routeur intelligent pour /dashboard/ :
    - Si un dossier actif est en session -> redirige vers /dashboard/<slug>/
    - Si l'utilisateur n'a accès qu'à 1 seul dossier -> l'active et redirige vers /dashboard/<slug>/
    - Sinon -> redirige vers la Galerie /dossiers/ pour choisir un espace de travail.
    """
    active_slug = request.session.get('active_dossier_slug')
    accessible = get_accessible_dossiers_for_user(request.user)

    if active_slug and accessible.filter(slug=active_slug).exists():
        return redirect('dashboard:dossier_dashboard', slug=active_slug)

    if accessible.count() == 1:
        dossier = accessible.first()
        request.session['active_dossier_id'] = str(dossier.id)
        request.session['active_dossier_slug'] = dossier.slug
        return redirect('dashboard:dossier_dashboard', slug=dossier.slug)

    return redirect('dossiers:list')


@login_required
def dossier_dashboard(request, slug):
    """
    Tableau de bord contextuel pour un dossier spécifique : /dashboard/<slug>/
    Active l'espace de travail en session et rend le dashboard adapté.
    """
    dossier = get_dossier_by_slug(slug)
    if not dossier:
        messages.error(request, "Dossier introuvable.")
        return redirect('dossiers:list')

    # Contrôle de sécurité
    accessible = get_accessible_dossiers_for_user(request.user)
    if not request.user.is_superuser and not accessible.filter(id=dossier.id).exists():
        messages.error(request, f"Vous n'êtes pas autorisé à accéder au dossier « {dossier.nom} ».")
        return redirect('dossiers:list')

    # Activation en session
    request.session['active_dossier_id'] = str(dossier.id)
    request.session['active_dossier_slug'] = dossier.slug

    # Rendu adapté au territoire
    if dossier.type_territoire == 'universite' or dossier.slug == 'campus-uad-bambey':
        return universite(request)

    return _commune_dashboard(request)


@login_required
def _commune_dashboard(request):
    """Accueil communal de référence (Ngogom)."""
    user = request.user
    # Le citoyen n'a pas accès aux données foncières : son accueil reste la carte.
    if not user.can_view_commune:
        if user.is_role_communal:
            return redirect('commune:carte')
        return redirect('dashboard:universite')

    commune = Commune.objects.first()
    stats = commune.stats_bati() if commune else {
        'nb_villages': Village.objects.count(), 'nb_maisons': 0, 'nb_habitees': 0,
        'nb_non_habitees': 0, 'superficie_batie': 0,
    }
    nb_maisons = stats['nb_maisons']
    taux_habitation = round(stats['nb_habitees'] / nb_maisons * 100, 1) if nb_maisons else 0

    villages = Village.objects.annotate(
        nb_maisons=Count('maisons'),
        nb_habitees=Count('maisons', filter=Q(maisons__statut_occupation=Maison.HABITEE)),
        surface_batie=Sum('maisons__superficie'),
    ).order_by('-nb_maisons', 'nom')

    pistes = Piste.objects.aggregate(nb=Count('id'), longueur=Sum('longueur'))

    context = {
        'commune': commune,
        'stats': stats,
        'taux_habitation': taux_habitation,
        'superficie_batie_ha': round(stats['superficie_batie'] / 10000, 2),
        'villages': villages,
        'nb_pistes': pistes['nb'],
        'longueur_pistes_km': round((pistes['longueur'] or 0) / 1000, 2),
        'nb_orthophotos': OrthophotoCommune.objects.count(),
        'maisons_json': json.dumps([stats['nb_habitees'], stats['nb_non_habitees']]),
        'villages_labels': _json_script([v.nom for v in villages[:12]]),
        'villages_data': json.dumps([v.nb_maisons for v in villages[:12]]),
    }

    if user.can_manage_signalements:
        signalements = Signalement.objects.all()
        agg = signalements.aggregate(
            total=Count('id'),
            **{code: Count('id', filter=Q(statut=code)) for code, _ in Signalement.STATUTS},
        )
        par_categorie = dict(signalements.values_list('categorie').annotate(n=Count('id')))
        context.update({
            'sig_total': agg['total'],
            'sig_ouverts': agg['total'] - agg[Signalement.RESOLU],
            'sig_statuts': [
                {'libelle': lib, 'nb': agg[code], 'couleur': Signalement.STATUT_COULEURS[code],
                 'pct': round(agg[code] / agg['total'] * 100) if agg['total'] else 0}
                for code, lib in Signalement.STATUTS
            ],
            'categories_labels': json.dumps([lib for code, lib in Signalement.CATEGORIES], ensure_ascii=False),
            'categories_data': json.dumps([par_categorie.get(code, 0) for code, _ in Signalement.CATEGORIES]),
            'categories_couleurs': json.dumps([Signalement.CATEGORIE_STYLE[code][0] for code, _ in Signalement.CATEGORIES]),
            'signalements_recents': signalements.select_related('village')[:6],
        })

    return render(request, 'dashboard/commune.html', context)


@login_required
def universite(request):
    """Tableau de bord du campus de l'UAD."""
    if request.user.is_role_communal:
        return redirect('dashboard:index')
    # KPIs fonciers — le Campus est la seule référence de superficie totale,
    # il n'est jamais compté comme un espace ordinaire.
    campus = Campus.objects.first()
    superficie_totale   = campus.superficie if campus else 0
    superficie_occupee  = campus.superficie_occupee if campus else 0    # bâtiments + terrains sportifs + espaces verts + voiries
    superficie_reservee = campus.superficie_reservee if campus else 0   # sous-espaces de type Réservé (non occupés)
    superficie_libre    = campus.superficie_libre if campus else 0      # campus − occupée − réservée
    taux_occupation     = campus.taux_occupation if campus else 0       # occupée / campus × 100

    def _pct_campus(val):
        return round(val / superficie_totale * 100, 1) if superficie_totale else 0
    pct_libre    = _pct_campus(superficie_libre)
    pct_reservee = _pct_campus(superficie_reservee)

    # Détail de l'occupation — mêmes couches et même géométrie campus que
    # Campus.superficie_occupee, pour que le compte affiché reste toujours
    # cohérent avec la superficie occupée annoncée.
    if campus and campus.geometrie:
        nb_batiments_occ       = Batiment.objects.filter(geometrie__intersects=campus.geometrie).count()
        nb_terrains_sportifs   = Terrain.objects.filter(geometrie__intersects=campus.geometrie, type_terrain__icontains='sport').count()
        nb_espaces_verts_occ   = EspaceVert.objects.filter(geometrie__intersects=campus.geometrie).count()
        nb_voiries_occ         = Voirie.objects.filter(geometrie__intersects=campus.geometrie).count()
    else:
        nb_batiments_occ = nb_terrains_sportifs = nb_espaces_verts_occ = nb_voiries_occ = 0

    def _sup_statut(statut):
        return NouvelleConstruction.objects.filter(
            statut=statut
        ).aggregate(t=Sum('superficie_souhaitee'))['t'] or 0

    sup_approuvee  = _sup_statut(NouvelleConstruction.STATUT_APPROUVE)
    sup_en_cours   = _sup_statut(NouvelleConstruction.STATUT_EN_COURS)
    sup_allouee    = sup_approuvee + sup_en_cours
    superficie_prise = superficie_occupee

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
        'pct_libre': pct_libre,
        'pct_reservee': pct_reservee,
        'nb_batiments_occ':     nb_batiments_occ,
        'nb_terrains_sportifs': nb_terrains_sportifs,
        'nb_espaces_verts_occ': nb_espaces_verts_occ,
        'nb_voiries_occ':       nb_voiries_occ,
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
