import base64
import json as _json
import os
import shutil
import subprocess
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import domaine_required
from ..forms import FluxVideoImportForm
from ..models import FluxVideo, Mission, PhotoDrone
from ..selectors import get_flux_video_by_id, get_photo_drone_by_id


def _duree_video_secondes(filepath):
    """Interroge ffprobe (si présent) pour récupérer la durée d'un fichier vidéo."""
    if not shutil.which('ffprobe'):
        return None
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15,
        )
        return int(float(out.stdout.decode().strip()))
    except Exception:
        return None


@login_required
@domaine_required
def flux_video_import(request):
    """Import manuel d'un fichier vidéo existant."""
    form = FluxVideoImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        video = form.save(commit=False)
        video.taille_octets = video.fichier.size
        if not video.operateur:
            video.operateur = request.user.get_full_name() or request.user.username
        video.save()
        video.duree_secondes = _duree_video_secondes(video.fichier.path)
        video.save(update_fields=['duree_secondes'])
        messages.success(request, f'Vidéo « {video.nom} » importée avec succès.')
        return redirect('drones:flux_videos')
    return render(request, 'drones/media/video_import.html', {'form': form})


@login_required
@domaine_required
def flux_videos_list(request):
    qs = FluxVideo.objects.all()
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    total_taille = sum(v.taille_octets or 0 for v in FluxVideo.objects.all())
    return render(request, 'drones/media/videos_list.html', {
        'page_obj': page,
        'total': FluxVideo.objects.count(),
        'total_taille': round(total_taille / 1048576, 1),
    })


@login_required
@domaine_required
def flux_video_delete(request, pk):
    video = get_flux_video_by_id(pk)
    if request.method == 'POST':
        if video.fichier and os.path.exists(video.fichier.path):
            os.remove(video.fichier.path)
        video.delete()
        messages.success(request, f'Vidéo « {video.nom} » supprimée.')
        return redirect('drones:flux_videos')
    return render(request, 'drones/communs/confirm_delete.html', {'obj': video})


@login_required
@domaine_required
def capture_photo(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requis'}, status=405)

    try:
        data = _json.loads(request.body)
        image_data = data.get('image', '')
        nom = data.get('nom', '').strip()
        mission_id = data.get('mission_id')
    except Exception:
        return JsonResponse({'error': 'Données invalides'}, status=400)

    if not image_data or ';base64,' not in image_data:
        return JsonResponse({'error': 'Image manquante'}, status=400)

    fmt, imgstr = image_data.split(';base64,')
    ext = fmt.split('/')[-1]
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nom = nom or f'Capture {ts}'
    filename = f'drone-{ts}.{ext}'

    try:
        content = ContentFile(base64.b64decode(imgstr))
    except Exception:
        return JsonResponse({'error': 'Décodage base64 échoué'}, status=400)

    mission = Mission.objects.filter(pk=mission_id).first() if mission_id else None

    photo = PhotoDrone(
        nom=nom,
        mission=mission,
        operateur=request.user.get_full_name() or request.user.username,
    )
    photo.image.save(filename, content, save=True)

    return JsonResponse({
        'status': 'ok',
        'id': photo.pk,
        'nom': photo.nom,
        'url': photo.image.url,
    })


@login_required
@domaine_required
def photos_drone_list(request):
    qs = PhotoDrone.objects.all()
    page = Paginator(qs, 16).get_page(request.GET.get('page'))
    return render(request, 'drones/media/photos_list.html', {
        'page_obj': page,
        'total': PhotoDrone.objects.count(),
    })


@login_required
@domaine_required
def photo_drone_delete(request, pk):
    photo = get_photo_drone_by_id(pk)
    if request.method == 'POST':
        if photo.image and os.path.exists(photo.image.path):
            os.remove(photo.image.path)
        photo.delete()
        messages.success(request, f'Photo « {photo.nom} » supprimée.')
        return redirect('drones:photos_drone')
    return render(request, 'drones/communs/confirm_delete.html', {'obj': photo})
