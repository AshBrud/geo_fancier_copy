"""
Vues Django pour le module de gestion des constructions, d'aide à la décision
et de suivi d'historique de chantiers (Urbanisme).
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.gis.geos import GEOSGeometry

from accounts.decorators import foncier_required
from dossiers.models import Dossier, ZoneSecteur, UniteBatie
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction
from urbanisme.forms import NouvelleConstructionForm, HistoriqueConstructionForm
from urbanisme.services import (
    recommander_emplacements_implantation,
    analyser_disponibilite_projet,
    mettre_a_jour_statut_construction,
)
from urbanisme.selectors import (
    get_projets_construction_qs,
    get_constructions_recentes,
    get_historique_travaux_qs,
    get_historique_annees_disponibles,
    get_espaces_constructibles_data,
)


@login_required
@foncier_required
def recommander_emplacements_view(request):
    """
    Endpoint AJAX : système d'aide à la décision — analyse et classe les
    sous-espaces Libres pour un type de projet et une superficie donnés.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

    type_construction = request.POST.get('type_construction', '').strip()
    try:
        superficie = float(request.POST.get('superficie_souhaitee', 0))
    except (TypeError, ValueError):
        superficie = 0.0

    if superficie <= 0:
        return JsonResponse({'error': 'Veuillez renseigner une superficie souhaitée valide.'}, status=400)

    active_dossier = getattr(request, 'active_dossier', None) or Dossier.objects.first()
    if not active_dossier:
        return JsonResponse({'error': "Aucun dossier territorial n'est défini : impossible d'analyser les emplacements."}, status=400)

    resultats = recommander_emplacements_implantation(type_construction, superficie, dossier=active_dossier)
    compatibles = [r for r in resultats if r['compatible']]

    return JsonResponse({
        'resultats': resultats,
        'nb_analyses': len(resultats),
        'nb_compatibles': len(compatibles),
        'meilleur': compatibles[0] if compatibles else None,
    })


@login_required
@foncier_required
def nouvelle_construction(request):
    """
    Formulaire et carte interactive pour tester la faisabilité d'une nouvelle construction
    et enregistrer la demande.
    """
    dossier = getattr(request, 'active_dossier', None)
    form = NouvelleConstructionForm(request.POST or None, dossier=dossier)
    resultat = None
    zones_alternatives = []

    espaces_data = get_espaces_constructibles_data(dossier=dossier)

    if request.method == 'POST' and form.is_valid():
        construction = form.save(commit=False)
        construction.demandeur = request.user
        if dossier and not construction.dossier:
            construction.dossier = dossier

        espace_id = request.POST.get('espace_id', '').strip()
        zone_geojson = request.POST.get('zone_geojson', '').strip()

        if espace_id:
            try:
                zone_obj = ZoneSecteur.objects.get(pk=int(espace_id))
                if zone_obj.geometrie:
                    construction.zone_souhaitee = zone_obj.geometrie.convex_hull
                construction.zone_secteur = zone_obj
                construction.dossier = zone_obj.dossier
            except (ZoneSecteur.DoesNotExist, ValueError):
                messages.warning(request, 'Zone sélectionnée introuvable.')
        elif zone_geojson:
            try:
                construction.zone_souhaitee = GEOSGeometry(zone_geojson)
            except Exception:
                messages.warning(request, 'Zone dessinée invalide, veuillez recommencer.')

        construction.save()
        disponible, rapport, alternatives, stats = analyser_disponibilite_projet(construction)
        zones_alternatives = list(alternatives)
        resultat = {
            'construction': construction,
            'disponible': disponible,
            'rapport': rapport,
            'stats': stats,
        }
        messages.success(request, 'Analyse de disponibilité effectuée.')
        form = NouvelleConstructionForm(dossier=dossier)

    recentes = get_constructions_recentes(dossier=dossier, limit=5)

    return render(request, 'urbanisme/constructions/simulation.html', {
        'form': form,
        'resultat': resultat,
        'zones_alternatives': zones_alternatives,
        'recentes': recentes,
        'espaces_json': json.dumps(espaces_data, ensure_ascii=False),
        'espaces_count': len(espaces_data),
    })


@login_required
@foncier_required
def constructions_list(request):
    """
    Liste paginée et interactive des projets de construction (V2).
    - Table épurée avec lignes cliquables connectées au SlideOver
    - Modale d'ajout direct sans rechargement de page
    """
    dossier = getattr(request, 'active_dossier', None)
    if not dossier:
        from dossiers.selectors import get_accessible_dossiers_for_user
        dossier = get_accessible_dossiers_for_user(request.user).first()

    # Formulaire de création pour la modale
    creation_form = NouvelleConstructionForm(request.POST or None, dossier=dossier)
    if request.method == 'POST' and 'submit_projet' in request.POST:
        if creation_form.is_valid():
            projet = creation_form.save(commit=False)
            projet.dossier = dossier
            if not projet.demandeur:
                projet.demandeur = request.user
            projet.save()
            try:
                analyser_disponibilite_projet(projet)
            except Exception:
                pass
            messages.success(request, f"Projet « {projet.nom_projet} » enregistré avec succès.")
            return redirect(request.path)

    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '').strip()

    qs = get_projets_construction_qs(dossier=dossier, statut=statut, search_term=q)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'urbanisme/constructions/list.html', {
        'page_obj': page,
        'q': q,
        'statut': statut,
        'statuts': NouvelleConstruction.STATUTS,
        'creation_form': creation_form,
        'active_dossier': dossier,
    })


@login_required
@foncier_required
def construction_update_statut(request, pk):
    """Mise à jour du statut d'instruction avec réévaluation des projets concurrents."""
    construction = get_object_or_404(NouvelleConstruction, pk=pk)
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in dict(NouvelleConstruction.STATUTS):
            _, auto_rejetees = mettre_a_jour_statut_construction(construction, nouveau_statut)
            messages.success(request, f'Statut mis à jour : {construction.get_statut_display()}')

            if auto_rejetees:
                liste = ', '.join(f'« {c.nom_projet} »' for c in auto_rejetees)
                messages.warning(
                    request,
                    f'{len(auto_rejetees)} demande(s) automatiquement rejetée(s) '
                    f'faute de superficie suffisante dans la zone : {liste}.'
                )
    return redirect(request.META.get('HTTP_REFERER') or 'urbanisme:list')


@login_required
def historique_list(request):
    """Consultation de l'historique des travaux et rénovations."""
    annee = request.GET.get('annee', '').strip()
    type_travaux = request.GET.get('type', '').strip()

    qs = get_historique_travaux_qs(annee=annee, type_travaux=type_travaux)
    annees = get_historique_annees_disponibles()

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'urbanisme/historique/list.html', {
        'page_obj': page,
        'annee': annee,
        'type_travaux': type_travaux,
        'types': HistoriqueConstruction.TYPES_TRAVAUX,
        'annees': annees,
    })


@login_required
@foncier_required
def historique_create(request):
    """Enregistrement d'un nouvel historique de travaux."""
    dossier = getattr(request, 'active_dossier', None)
    form = HistoriqueConstructionForm(request.POST or None, dossier=dossier)
    if request.method == 'POST' and form.is_valid():
        h = form.save()
        cible = h.unite_batie.nom if h.unite_batie else (h.batiment.nom if h.batiment else "Bâti")
        messages.success(request, f'Historique enregistré pour {cible}.')
        return redirect('urbanisme:historique')

    return render(request, 'urbanisme/historique/form.html', {
        'form': form,
        'action': 'Enregistrer un historique'
    })


@login_required
@foncier_required
def construction_delete(request, pk):
    """Suppression d'une demande de construction."""
    construction = get_object_or_404(NouvelleConstruction, pk=pk)
    if request.method == 'POST':
        nom = construction.nom_projet
        construction.delete()
        messages.success(request, f'Demande « {nom} » supprimée.')
        return redirect(request.META.get('HTTP_REFERER') or 'urbanisme:list')
    return render(request, 'urbanisme/constructions/confirm_delete.html', {
        'construction': construction
    })


@login_required
@foncier_required
def historique_delete(request, pk):
    """Suppression d'un enregistrement d'historique."""
    h = get_object_or_404(HistoriqueConstruction, pk=pk)
    if request.method == 'POST':
        h.delete()
        messages.success(request, 'Entrée d\'historique supprimée.')
        return redirect('urbanisme:historique')
    return render(request, 'urbanisme/constructions/generic_delete.html', {'obj': h})
