from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
import json
from .models import Espace, Batiment, FonctionBatiment
from .forms import EspaceForm, BatimentForm
from accounts.decorators import foncier_required


# --- Cartographie ---

@login_required
def cartographie(request):
    from drones.models import MissionDrone
    missions = list(
        MissionDrone.objects.filter(tiles_url__gt='')
        .values('id', 'nom', 'date_mission', 'tiles_url', 'statut')
        .order_by('-date_mission')
    )
    for m in missions:
        m['date_mission'] = m['date_mission'].strftime('%d/%m/%Y') if m['date_mission'] else ''
    return render(request, 'cartographie/map.html', {
        'orthophotos_json': json.dumps(missions, ensure_ascii=False),
    })


# --- Espaces ---

@login_required
@foncier_required
def espaces_list(request):
    qs = Espace.objects.all()
    q = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    if type_filter:
        qs = qs.filter(type_espace=type_filter)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    stats = {t[0]: Espace.objects.filter(type_espace=t[0]).aggregate(
        count=Count('id'), total=Sum('superficie'))
        for t in Espace.TYPES}
    return render(request, 'foncier/espaces_list.html', {
        'page_obj': page, 'q': q, 'type_filter': type_filter,
        'types': Espace.TYPES, 'stats': stats,
    })


@login_required
@foncier_required
def espace_create(request):
    form = EspaceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        espace = form.save()
        messages.success(request, f'Espace « {espace.nom} » créé avec succès.')
        return redirect('foncier:espaces')
    return render(request, 'foncier/espace_form.html', {
        'form': form, 'action': 'Ajouter un espace', 'obj': None
    })


@login_required
@foncier_required
def espace_update(request, pk):
    espace = get_object_or_404(Espace, pk=pk)
    form = EspaceForm(request.POST or None, instance=espace)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Espace « {espace.nom} » modifié.')
        return redirect('foncier:espaces')
    return render(request, 'foncier/espace_form.html', {
        'form': form, 'action': 'Modifier l\'espace', 'obj': espace
    })


@login_required
@foncier_required
def espace_delete(request, pk):
    espace = get_object_or_404(Espace, pk=pk)
    if request.method == 'POST':
        nom = espace.nom
        espace.delete()
        messages.success(request, f'Espace « {nom} » supprimé.')
        return redirect('foncier:espaces')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': espace, 'type': 'l\'espace', 'back_url': 'foncier:espaces'
    })


# --- Bâtiments ---

@login_required
def batiments_list(request):
    qs = Batiment.objects.select_related('fonction').all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'foncier/batiments_list.html', {
        'page_obj': page, 'q': q,
        'total_batiments': Batiment.objects.count(),
        'superficie_totale': Batiment.objects.aggregate(s=Sum('superficie'))['s'] or 0,
    })


@login_required
def batiment_detail(request, pk):
    batiment = get_object_or_404(Batiment, pk=pk)
    return render(request, 'foncier/batiment_detail.html', {'batiment': batiment})


@login_required
@foncier_required
def batiment_create(request):
    form = BatimentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        bat = form.save()
        messages.success(request, f'Bâtiment « {bat.nom} » créé avec succès.')
        return redirect('foncier:batiments')
    return render(request, 'foncier/batiment_form.html', {
        'form': form, 'action': 'Ajouter un bâtiment', 'obj': None
    })


@login_required
@foncier_required
def batiment_update(request, pk):
    bat = get_object_or_404(Batiment, pk=pk)
    form = BatimentForm(request.POST or None, request.FILES or None, instance=bat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Bâtiment « {bat.nom} » modifié.')
        return redirect('foncier:batiments')
    return render(request, 'foncier/batiment_form.html', {
        'form': form, 'action': 'Modifier le bâtiment', 'obj': bat
    })


@login_required
@foncier_required
def batiment_delete(request, pk):
    bat = get_object_or_404(Batiment, pk=pk)
    if request.method == 'POST':
        nom = bat.nom
        bat.delete()
        messages.success(request, f'Bâtiment « {nom} » supprimé.')
        return redirect('foncier:batiments')
    return render(request, 'foncier/confirm_delete.html', {
        'obj': bat, 'type': 'le bâtiment', 'back_url': 'foncier:batiments'
    })
