from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from dossiers.models import Dossier, ZoneSecteur, UniteBatie, ReseauLineaire, SignalementDommage
from drones.models import Orthophoto, Mission
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction
from accounts.models import CustomUser, ActivityLog
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
def dossier_dashboard(request, slug=None, dossier_slug=None):
    """
    Tableau de bord contextuel pour un dossier spécifique :
    - Route V2 Dossier-First : /{slug}/dashboard/
    - Route legacy : /dashboard/<slug>/
    Active l'espace de travail en session et rend le dashboard adapté.
    """
    dossier = getattr(request, 'active_dossier', None)
    if not dossier:
        target_slug = slug or dossier_slug or request.session.get('active_dossier_slug')
        if target_slug:
            dossier = get_dossier_by_slug(target_slug)

    if not dossier:
        messages.error(request, "Dossier introuvable.")
        return redirect('dossiers:list')

    # Contrôle de sécurité
    accessible = get_accessible_dossiers_for_user(request.user)
    if not request.user.is_superuser and not accessible.filter(id=dossier.id).exists():
        messages.error(request, f"Vous n'êtes pas autorisé à accéder au dossier « {dossier.nom} ».")
        return redirect('dossiers:list')

    # Activation en session & requête
    request.session['active_dossier_id'] = str(dossier.id)
    request.session['active_dossier_slug'] = dossier.slug
    request.active_dossier = dossier

    # Activation en session & requête
    request.session['active_dossier_id'] = str(dossier.id)
    request.session['active_dossier_slug'] = dossier.slug
    request.active_dossier = dossier

    return render_dossier_dashboard(request, dossier)


@login_required
def render_dossier_dashboard(request, dossier):
    """
    Tableau de bord territorial unifié V2 :
    S'adapte dynamiquement à la typologie du territoire (commune, campus, zone industrielle, etc.)
    grâce au dictionnaire de terminologie et aux modules activés.
    """
    from dossiers.services.service_navigation import get_term
    user = request.user
    modules = dossier.configuration_modules or {}

    # ── Terminologie dynamique selon le territoire ──
    term_zone_singular = get_term(dossier, 'zone_singular', 'Subdivision')
    term_zone_plural = get_term(dossier, 'zone_plural', 'Subdivisions')
    term_bati_singular = get_term(dossier, 'bati_singular', 'Bâtiment')
    term_bati_plural = get_term(dossier, 'bati_plural', 'Bâtiments')
    term_reseau_singular = get_term(dossier, 'reseau_singular', 'Réseau')
    term_reseau_plural = get_term(dossier, 'reseau_plural', 'Réseaux & Voies')

    # ── Requêtes spatiales scopées au dossier actif ──
    ub_qs = UniteBatie.objects.filter(dossier=dossier)
    zs_qs = ZoneSecteur.objects.filter(dossier=dossier)
    rl_qs = ReseauLineaire.objects.filter(dossier=dossier)
    nc_base = NouvelleConstruction.objects.filter(dossier=dossier)
    ortho_qs = Orthophoto.objects.filter(Q(mission__dossier=dossier) | Q(mission__isnull=True))
    mission_qs = Mission.objects.filter(dossier=dossier)

    # ── Superficie globale du territoire ──
    superficie_totale = 0.0
    if dossier.superficie_m2:
        superficie_totale = float(dossier.superficie_m2)
    elif dossier.emprise:
        try:
            srid = getattr(dossier, 'srid_projection', 32628) or 32628
            superficie_totale = float(dossier.emprise.transform(srid, clone=True).area)
        except Exception:
            superficie_totale = float(zs_qs.aggregate(s=Sum('superficie_m2'))['s'] or 0.0)
    else:
        superficie_totale = float(zs_qs.aggregate(s=Sum('superficie_m2'))['s'] or 0.0)

    # ── Bâti & Recensement ──
    total_batiments = ub_qs.count()
    nb_habitees = ub_qs.filter(statut_occupation=UniteBatie.OCCUPATION_HABITEE).count()
    nb_non_habitees = max(0, total_batiments - nb_habitees)
    superficie_batie = float(ub_qs.aggregate(s=Sum('superficie_m2'))['s'] or 0.0)
    superficie_occupee = superficie_batie
    taux_occupation = round(superficie_occupee / superficie_totale * 100, 1) if superficie_totale else 0
    taux_habitation = round(nb_habitees / total_batiments * 100, 1) if total_batiments else 0

    # ── Subdivisions spatiales ──
    total_zones = zs_qs.count()
    superficie_reservee = float(zs_qs.filter(type_zone=ZoneSecteur.TYPE_ESPACE_RESERVE).aggregate(s=Sum('superficie_m2'))['s'] or 0.0)
    superficie_libre = max(0.0, superficie_totale - superficie_occupee - superficie_reservee) if superficie_totale else 0.0
    nb_espaces_libres = zs_qs.filter(type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE).count()

    # ── Réseaux & Linéaires ──
    reseaux_agg = rl_qs.aggregate(nb=Count('id'), longueur=Sum('longueur_metres'))
    total_reseaux = reseaux_agg['nb'] or 0
    longueur_reseaux_km = round((reseaux_agg['longueur'] or 0) / 1000, 2)

    # ── Top Subdivisions avec bâti ──
    zones_top = zs_qs.annotate(
        nb_batiments=Count('unites_baties'),
        nb_habitees=Count('unites_baties', filter=Q(unites_baties__statut_occupation=UniteBatie.OCCUPATION_HABITEE)),
        surface_batie=Sum('unites_baties__superficie_m2'),
    ).order_by('-nb_batiments', 'nom')[:12]

    zones_labels = [z.nom for z in zones_top]
    zones_data = [z.nb_batiments for z in zones_top]

    # ── Capacité constructible & Urbanisme ──
    has_urbanisme = modules.get('mod_urbanisme', True)
    sup_constructible_totale = superficie_libre + (superficie_reservee * 0.5)

    def _sup_statut(statut):
        return float(nc_base.filter(statut=statut).aggregate(t=Sum('superficie_souhaitee'))['t'] or 0)

    sup_approuvee = _sup_statut(NouvelleConstruction.STATUT_APPROUVE)
    sup_en_cours = _sup_statut(NouvelleConstruction.STATUT_EN_COURS)
    sup_allouee = sup_approuvee + sup_en_cours
    sup_constr_nette = max(0.0, sup_constructible_totale - sup_allouee)

    def _pct(val, total):
        return round(val / total * 100, 1) if total else 0

    pct_alloue = _pct(sup_allouee, sup_constructible_totale)
    pct_approuvee = _pct(sup_approuvee, sup_constructible_totale)
    pct_en_cours = _pct(sup_en_cours, sup_constructible_totale)
    nb_engagees = nc_base.filter(statut__in=NouvelleConstruction.STATUTS_ENGAGES).count()
    constructions_en_cours = nc_base.filter(statut='en_cours').count()
    constructions_approuvees = nc_base.filter(statut='approuvee').count()
    constructions_recentes = nc_base.select_related('demandeur').order_by('-date_demande')[:5]

    # ── Drones & Imagerie ──
    has_drones = modules.get('mod_drones', True)
    total_missions = mission_qs.count()
    missions_integrees = mission_qs.filter(statut=Mission.STATUT_INTEGREE).count()
    total_orthophotos = ortho_qs.count()
    orthophotos_recentes = ortho_qs.order_by('-date_ajout')[:4]

    # ── Signalements & Incidents ──
    has_signalements = getattr(user, 'can_manage_signalements', False) or modules.get('mod_signalements', True)
    signalements_context = {}
    if has_signalements:
        sig_qs = SignalementDommage.objects.filter(dossier=dossier)
        agg_sig = sig_qs.aggregate(
            total=Count('id'),
            **{code: Count('id', filter=Q(statut=code)) for code, _ in SignalementDommage.STATUTS},
        )
        par_categorie = dict(sig_qs.values_list('categorie').annotate(n=Count('id')))
        signalements_context = {
            'sig_total': agg_sig['total'],
            'sig_ouverts': agg_sig['total'] - (agg_sig.get(SignalementDommage.STATUT_RESOLU, 0)),
            'sig_statuts': [
                {'libelle': lib, 'nb': agg_sig.get(code, 0), 'couleur': '#6366F1',
                 'pct': round(agg_sig.get(code, 0) / agg_sig['total'] * 100) if agg_sig['total'] else 0}
                for code, lib in SignalementDommage.STATUTS
            ],
            'categories_labels': json.dumps([lib for code, lib in SignalementDommage.CATEGORIES], ensure_ascii=False),
            'categories_data': json.dumps([par_categorie.get(code, 0) for code, _ in SignalementDommage.CATEGORIES]),
            'categories_couleurs': json.dumps(['#EF4444' for _ in SignalementDommage.CATEGORIES]),
            'signalements_recents': sig_qs.select_related('zone_secteur')[:6],
        }

    # ── Donut de répartition des surfaces ──
    chart_names = ['Espace libre', 'Espace occupé / bâti', 'Espace réservé']
    chart_colors = ['#16A34A', '#DC2626', '#F59E0B']
    chart_data = [
        round(superficie_libre / 10000, 2),
        round(superficie_occupee / 10000, 2),
        round(superficie_reservee / 10000, 2),
    ]

    # ── Évolution des constructions & chantiers ──
    from django.db.models.functions import ExtractYear
    hc_base = HistoriqueConstruction.objects.filter(unite_batie__dossier=dossier)
    histo_annees = (
        hc_base
        .annotate(annee=ExtractYear('date_debut'))
        .values('annee')
        .annotate(count=Count('id'))
        .order_by('annee')
    )
    evol_labels = [str(h['annee']) for h in histo_annees]
    evol_data = [h['count'] for h in histo_annees]

    batiments_recents = ub_qs.order_by('-date_creation')[:5]

    try:
        from accounts.models import ActivityLog
        activites = list(ActivityLog.objects.select_related('user').order_by('-timestamp')[:8])
    except Exception:
        activites = []

    context = {
        'dossier': dossier,
        'modules': modules,
        'has_urbanisme': has_urbanisme,
        'has_drones': has_drones,
        'has_signalements': has_signalements,

        # Terminologie dynamique
        'term_zone_singular': term_zone_singular,
        'term_zone_plural': term_zone_plural,
        'term_bati_singular': term_bati_singular,
        'term_bati_plural': term_bati_plural,
        'term_reseau_singular': term_reseau_singular,
        'term_reseau_plural': term_reseau_plural,

        # Superficies & Occupation
        'superficie_totale': round(superficie_totale / 10000, 2),
        'superficie_totale_m2': round(superficie_totale),
        'superficie_occupee': round(superficie_occupee / 10000, 2),
        'superficie_batie_ha': round(superficie_batie / 10000, 2),
        'superficie_libre': round(superficie_libre / 10000, 2),
        'superficie_reservee': round(superficie_reservee / 10000, 2),
        'taux_occupation': taux_occupation,
        'taux_habitation': taux_habitation,
        'pct_libre': round(superficie_libre / superficie_totale * 100, 1) if superficie_totale else 0,
        'pct_reservee': round(superficie_reservee / superficie_totale * 100, 1) if superficie_totale else 0,

        # Compteurs spatiaux
        'total_zones': total_zones,
        'total_espaces': total_zones,
        'nb_espaces_libres': nb_espaces_libres,
        'total_batiments': total_batiments,
        'nb_maisons': total_batiments,
        'nb_habitees': nb_habitees,
        'nb_non_habitees': nb_non_habitees,
        'total_reseaux': total_reseaux,
        'nb_pistes': total_reseaux,
        'nb_voiries_occ': total_reseaux,
        'longueur_reseaux_km': longueur_reseaux_km,
        'longueur_pistes_km': longueur_reseaux_km,

        # Données de répartition par subdivision
        'zones_top': zones_top,
        'villages': zones_top,
        'zones_labels': json.dumps(zones_labels, ensure_ascii=False),
        'zones_data': json.dumps(zones_data),
        'villages_labels': json.dumps(zones_labels, ensure_ascii=False),
        'villages_data': json.dumps(zones_data),
        'maisons_json': json.dumps([nb_habitees, nb_non_habitees]),

        # Capacité constructible (Urbanisme)
        'sup_constructible_totale': round(sup_constructible_totale),
        'sup_constructible_totale_ha': round(sup_constructible_totale / 10000, 2),
        'sup_allouee': round(sup_allouee),
        'sup_allouee_ha': round(sup_allouee / 10000, 2),
        'sup_approuvee': round(sup_approuvee),
        'sup_en_cours': round(sup_en_cours),
        'sup_constr_nette': round(sup_constr_nette),
        'sup_constr_nette_ha': round(sup_constr_nette / 10000, 2),
        'pct_alloue': pct_alloue,
        'pct_approuvee': pct_approuvee,
        'pct_en_cours': pct_en_cours,
        'nb_engagees': nb_engagees,
        'total_constructions': nc_base.count(),
        'constructions_en_cours': constructions_en_cours,
        'constructions_approuvees': constructions_approuvees,
        'constructions_recentes': constructions_recentes,

        # Drones
        'total_missions': total_missions,
        'missions_integrees': missions_integrees,
        'total_orthophotos': total_orthophotos,
        'orthophotos_recentes': orthophotos_recentes,

        # Donut Chart & Graphiques
        'chart_labels': json.dumps(chart_names),
        'chart_data': json.dumps(chart_data),
        'chart_colors': json.dumps(chart_colors),
        'evol_labels': json.dumps(evol_labels),
        'evol_data': json.dumps(evol_data),

        # Activités et récents
        'activites': activites,
        'batiments_recents': batiments_recents,

        # Compatibilité
        'commune': dossier,
        'campus': dossier,
    }
    context.update(signalements_context)

    return render(request, 'dashboard/index.html', context)



