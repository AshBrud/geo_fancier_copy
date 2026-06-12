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
    form = NouvelleConstructionForm(request.POST or None)
    resultat = None
    zones_alternatives = []

    if request.method == 'POST' and form.is_valid():
        construction = form.save(commit=False)
        construction.demandeur = request.user

        zone_geojson = request.POST.get('zone_geojson', '').strip()
        if zone_geojson:
            try:
                construction.zone_souhaitee = GEOSGeometry(zone_geojson)
            except Exception:
                messages.warning(request, 'Zone dessinée invalide, veuillez recommencer.')

        construction.save()
        disponible, rapport, alternatives = construction.analyser_disponibilite()
        zones_alternatives = list(alternatives)
        resultat = {
            'construction': construction,
            'disponible': disponible,
            'rapport': rapport,
        }
        messages.success(request, 'Analyse de disponibilité effectuée.')
        form = NouvelleConstructionForm()

    recentes = NouvelleConstruction.objects.select_related('demandeur').all()[:5]
    return render(request, 'constructions/nouvelle_construction.html', {
        'form': form,
        'resultat': resultat,
        'zones_alternatives': zones_alternatives,
        'recentes': recentes,
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
        if nouveau_statut in dict(NouvelleConstruction.STATUTS):
            construction.statut = nouveau_statut
            construction.save()
            messages.success(request, f'Statut mis à jour : {construction.get_statut_display()}')
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
def historique_delete(request, pk):
    h = get_object_or_404(HistoriqueConstruction, pk=pk)
    if request.method == 'POST':
        h.delete()
        messages.success(request, 'Entrée d\'historique supprimée.')
        return redirect('constructions:historique')
    return render(request, 'constructions/confirm_delete.html', {'obj': h})
