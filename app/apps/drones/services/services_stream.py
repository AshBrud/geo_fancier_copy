import os
import shutil
import subprocess
import sys
import signal as _signal
from datetime import datetime
from django.conf import settings
from django.shortcuts import get_object_or_404

from ..models import FluxVideo

# Enregistrements actifs (par utilisateur — clé = user.pk)
_active_recordings = {}
# Diffusions simulées actives (vidéo publiée en boucle vers MediaMTX comme flux live)
_active_broadcasts = {}


def demarrer_enregistrement(uid, rtsp_url, nom=None):
    if uid in _active_recordings:
        return {'error': 'Un enregistrement est déjà en cours', 'status_code': 400}

    if not shutil.which('ffmpeg'):
        return {'error': 'FFmpeg non installé sur le serveur.', 'status_code': 500}

    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nom = nom or f'Flux drone {ts}'
    filename = f'flux-drone-{ts}.mp4'
    save_dir = os.path.join(settings.MEDIA_ROOT, 'flux_videos')
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)

    cmd = [
        'ffmpeg', '-y',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-c', 'copy',
        '-movflags', 'frag_keyframe+empty_moov',
        filepath,
    ]

    kwargs = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    except Exception as e:
        return {'error': f'Impossible de démarrer FFmpeg : {e}', 'status_code': 500}

    _active_recordings[uid] = {
        'proc': proc,
        'filepath': filepath,
        'nom': nom,
        'start_time': datetime.now(),
        'rtsp_url': rtsp_url,
    }
    return {'status': 'started', 'nom': nom}


def arreter_enregistrement(uid, user):
    rec = _active_recordings.pop(uid, None)
    if not rec:
        return {'error': 'Aucun enregistrement en cours', 'status_code': 400}

    proc = rec['proc']
    try:
        if sys.platform == 'win32':
            proc.send_signal(_signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(_signal.SIGINT)
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

    duree = int((datetime.now() - rec['start_time']).total_seconds())
    filepath = rec['filepath']

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        rel = os.path.relpath(filepath, settings.MEDIA_ROOT).replace('\\', '/')
        video = FluxVideo.objects.create(
            nom=rec['nom'],
            fichier=rel,
            duree_secondes=duree,
            taille_octets=os.path.getsize(filepath),
            source_rtsp=rec['rtsp_url'],
            operateur=user.get_full_name() or user.username,
        )
        return {
            'status': 'stopped',
            'id': video.pk,
            'nom': video.nom,
            'duree': video.duree_formatee,
            'taille_mb': video.taille_mb,
        }

    return {'status': 'stopped', 'warning': 'Fichier vide ou non créé'}


def demarrer_diffusion(uid, video_id, rtsp_url, boucle=True):
    if not shutil.which('ffmpeg'):
        return {'error': 'FFmpeg non installé sur le serveur.', 'status_code': 500}

    video = get_object_or_404(FluxVideo, pk=video_id)
    if not (video.fichier and os.path.exists(video.fichier.path)):
        return {'error': 'Fichier vidéo introuvable sur le serveur.', 'status_code': 404}

    if uid in _active_broadcasts:
        return {'error': 'Une diffusion est déjà en cours', 'status_code': 400}

    cmd = ['ffmpeg', '-re']
    if boucle:
        cmd += ['-stream_loop', '-1']
    cmd += [
        '-i', video.fichier.path,
        '-c', 'copy',
        '-f', 'rtsp',
        '-rtsp_transport', 'tcp',
        rtsp_url,
    ]

    kwargs = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    except Exception as e:
        return {'error': f'Impossible de démarrer FFmpeg : {e}', 'status_code': 500}

    _active_broadcasts[uid] = {
        'proc': proc,
        'video': video.nom,
        'rtsp_url': rtsp_url,
        'start_time': datetime.now(),
    }
    return {'status': 'started', 'nom': video.nom}


def arreter_diffusion(uid):
    bc = _active_broadcasts.pop(uid, None)
    if not bc:
        return {'error': 'Aucune diffusion en cours', 'status_code': 400}

    proc = bc['proc']
    try:
        if sys.platform == 'win32':
            proc.send_signal(_signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(_signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

    return {'status': 'stopped', 'nom': bc['video']}
