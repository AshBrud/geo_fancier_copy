from django.db.models import Q
from django.shortcuts import get_object_or_404

from ..models import FluxVideo, PhotoDrone


def get_flux_videos_queryset(q=None):
    """Queryset filtrable pour les flux vidéo enregistrés."""
    qs = FluxVideo.objects.all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(operateur__icontains=q))
    return qs.order_by('-date_enregistrement')


def get_flux_video_by_id(pk):
    """Récupère une vidéo de flux par sa clé primaire."""
    return get_object_or_404(FluxVideo, pk=pk)


def get_photos_drone_queryset(mission=None, q=None):
    """Queryset filtrable pour les photographies drone."""
    qs = PhotoDrone.objects.select_related('mission')
    if mission:
        qs = qs.filter(mission=mission)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(operateur__icontains=q) | Q(notes__icontains=q))
    return qs.order_by('-date_capture')


def get_photo_drone_by_id(pk):
    """Récupère une photo drone par son identifiant."""
    return get_object_or_404(PhotoDrone.objects.select_related('mission'), pk=pk)
