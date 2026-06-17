from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import NouvelleConstruction, HistoriqueConstruction
from .forms import NouvelleConstructionForm, HistoriqueConstructionForm
from accounts.decorators import foncier_required


# --- Nouvelle Construction ---

@login_required
@foncier_required
def nouvelle_construction(request):
    from django.contrib.gis.geos import GEOSGeometry
    from foncier.models import Espace
    import json

    form = NouvelleConstructionForm(request.POST or None)
    resultat = None
    zones_alternatives = []

    # Sérialiser les espaces libres pour la carte, avec calcul de superficie disponible
    espaces_libres = Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).order_by('nom')
    espaces_data = []
    for e in espaces_libres:
        if e.geometrie:
            sup_engagee = sum(
                c.superficie_souhaitee or 0
                for c in NouvelleConstruction.objects.filter(
                    statut__in=NouvelleConstruction.STATUTS_ENGAGES,
                    zone_souhaitee__intersects=e.geometrie,
                )
            )
            sup_constructible = (e.superficie or 0) * (e.taux_occupation / 100)
            sup_disponible = max(0.0, sup_constructible - sup_engagee)

            espaces_data.append({
                'id': e.pk,
                'nom': e.nom,
                'code': e.code,
                'superficie': e.superficie or 0,
                'taux_occupation': e.taux_occupation,
                'sup_constructible': sup_constructible,
                'sup_engagee': sup_engagee,
                'sup_disponible': sup_disponible,
                'geojson': json.loads(e.geometrie.geojson),
            })

    if request.method == 'POST' and form.is_valid():
        construction = form.save(commit=False)
        construction.demandeur = request.user

        espace_id = request.POST.get('espace_id', '').strip()
        zone_geojson = request.POST.get('zone_geojson', '').strip()

        if espace_id:
            try:
                espace_obj = Espace.objects.get(pk=int(espace_id))
                if espace_obj.geometrie:
                    construction.zone_souhaitee = espace_obj.geometrie.convex_hull
                construction.espace_souhaitee_id = int(espace_id)
            except (Espace.DoesNotExist, ValueError):
                messages.warning(request, 'Espace sélectionné introuvable.')
        elif zone_geojson:
            try:
                construction.zone_souhaitee = GEOSGeometry(zone_geojson)
            except Exception:
                messages.warning(request, 'Zone dessinée invalide, veuillez recommencer.')

        construction.save()
        disponible, rapport, alternatives, stats = construction.analyser_disponibilite()
        zones_alternatives = list(alternatives)
        resultat = {
            'construction': construction,
            'disponible': disponible,
            'rapport': rapport,
            'stats': stats,
        }
        messages.success(request, 'Analyse de disponibilité effectuée.')
        form = NouvelleConstructionForm()

    recentes = NouvelleConstruction.objects.select_related('demandeur').all()[:5]
    return render(request, 'constructions/nouvelle_construction.html', {
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
    qs = NouvelleConstruction.objects.select_related('demandeur').all()
    q = request.GET.get('q', '')
    statut = request.GET.get('statut', '')
    if q:
        qs = qs.filter(Q(nom_projet__icontains=q) | Q(type_construction__icontains=q))
    if statut:
        qs = qs.filter(statut=statut)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'constructions/constructions_list.html', {
        'page_obj': page, 'q': q, 'statut': statut,
        'statuts': NouvelleConstruction.STATUTS,
    })


@login_required
@foncier_required
def construction_update_statut(request, pk):
    construction = get_object_or_404(NouvelleConstruction, pk=pk)
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        ancien_statut = construction.statut
        if nouveau_statut in dict(NouvelleConstruction.STATUTS):
            construction.statut = nouveau_statut
            construction.save()
            messages.success(request, f'Statut mis à jour : {construction.get_statut_display()}')

            # Rejet automatique des demandes concurrentes incompatibles
            # Se déclenche depuis n'importe quel statut non-engagé vers un statut engagé
            if (nouveau_statut in NouvelleConstruction.STATUTS_ENGAGES
                    and ancien_statut not in NouvelleConstruction.STATUTS_ENGAGES):
                auto_rejetees = construction.rejeter_concurrents()
                if auto_rejetees:
                    liste = ', '.join(f'« {c.nom_projet} »' for c in auto_rejetees)
                    messages.warning(
                        request,
                        f'{len(auto_rejetees)} demande(s) automatiquement rejetée(s) '
                        f'faute de superficie suffisante dans la zone : {liste}.'
                    )
    return redirect('constructions:list')


# --- Historique ---

@login_required
def historique_list(request):
    qs = HistoriqueConstruction.objects.select_related('batiment').all()
    annee = request.GET.get('annee', '')
    type_travaux = request.GET.get('type', '')
    if annee:
        qs = qs.filter(date_debut__year=annee)
    if type_travaux:
        qs = qs.filter(type_travaux=type_travaux)
    annees = HistoriqueConstruction.objects.dates('date_debut', 'year', order='DESC')
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'constructions/historique_list.html', {
        'page_obj': page, 'annee': annee, 'type_travaux': type_travaux,
        'types': HistoriqueConstruction.TYPES_TRAVAUX, 'annees': annees,
    })


@login_required
@foncier_required
def historique_create(request):
    form = HistoriqueConstructionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        h = form.save()
        messages.success(request, f'Historique enregistré pour {h.batiment.nom}.')
        return redirect('constructions:historique')
    return render(request, 'constructions/historique_form.html', {
        'form': form, 'action': 'Enregistrer un historique'
    })


@login_required
@foncier_required
def construction_delete(request, pk):
    construction = get_object_or_404(NouvelleConstruction, pk=pk)
    if request.method == 'POST':
        nom = construction.nom_projet
        construction.delete()
        messages.success(request, f'Demande « {nom} » supprimée.')
        return redirect('constructions:list')
    return render(request, 'constructions/construction_confirm_delete.html', {
        'construction': construction
    })


@login_required
@foncier_required
def historique_delete(request, pk):
    h = get_object_or_404(HistoriqueConstruction, pk=pk)
    if request.method == 'POST':
        h.delete()
        messages.success(request, 'Entrée d\'historique supprimée.')
        return redirect('constructions:historique')
    return render(request, 'constructions/confirm_delete.html', {'obj': h})
