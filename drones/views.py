from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import MissionDrone, Orthophoto
from .forms import MissionDroneForm, OrthophotoForm
from accounts.decorators import domaine_required


@login_required
@domaine_required
def missions_list(request):
    missions = MissionDrone.objects.prefetch_related('orthophotos').all()
    paginator = Paginator(missions, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'drones/missions_list.html', {
        'page_obj': page,
        'total_missions': MissionDrone.objects.count(),
        'total_orthophotos': Orthophoto.objects.count(),
    })


@login_required
@domaine_required
def mission_create(request):
    form = MissionDroneForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mission = form.save()
        messages.success(request, f'Mission « {mission.nom} » créée.')
        return redirect('drones:missions')
    return render(request, 'drones/mission_form.html', {'form': form, 'action': 'Nouvelle mission'})


@login_required
@domaine_required
def mission_update(request, pk):
    mission = get_object_or_404(MissionDrone, pk=pk)
    form = MissionDroneForm(request.POST or None, instance=mission)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Mission « {mission.nom} » modifiée.')
        return redirect('drones:missions')
    return render(request, 'drones/mission_form.html', {
        'form': form, 'action': 'Modifier la mission', 'obj': mission
    })


@login_required
@domaine_required
def mission_delete(request, pk):
    mission = get_object_or_404(MissionDrone, pk=pk)
    if request.method == 'POST':
        nom = mission.nom
        mission.delete()
        messages.success(request, f'Mission « {nom} » supprimée.')
        return redirect('drones:missions')
    return render(request, 'drones/confirm_delete.html', {'obj': mission})


@login_required
@domaine_required
def orthophoto_add(request, mission_pk):
    mission = get_object_or_404(MissionDrone, pk=mission_pk)
    form = OrthophotoForm(request.POST or None, request.FILES or None,
                          initial={'mission': mission})
    if request.method == 'POST' and form.is_valid():
        ortho = form.save()
        messages.success(request, f'Orthophoto « {ortho.nom} » ajoutée.')
        return redirect('drones:missions')
    return render(request, 'drones/orthophoto_form.html', {
        'form': form, 'mission': mission
    })


@login_required
@domaine_required
def orthophoto_delete(request, pk):
    ortho = get_object_or_404(Orthophoto, pk=pk)
    if request.method == 'POST':
        mission_pk = ortho.mission.pk
        ortho.delete()
        messages.success(request, 'Orthophoto supprimée.')
        return redirect('drones:missions')
    return render(request, 'drones/confirm_delete.html', {'obj': ortho})
