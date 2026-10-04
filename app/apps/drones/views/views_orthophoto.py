import os
from datetime import date as _today
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import domaine_required
from ..forms import OrthophotoImportForm
from ..models import Mission, Orthophoto
from ..selectors import get_mission_by_id, get_orthophoto_by_id
from ..services import extraire_metadata_geotiff, generer_tuiles_locales


@login_required
@domaine_required
def import_orthophoto(request, pk=None):
    """Import d'une orthophoto avec extraction automatique des métadonnées GeoTIFF."""
    mission = get_mission_by_id(pk) if pk else None
    form = OrthophotoImportForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        ortho = form.save(commit=False)
        ortho.date_prise = _today.today()
        ortho.mission = mission
        ortho.save()

        ext = os.path.splitext(ortho.fichier.name)[1].lower()
        if ext in ('.tif', '.tiff', '.geotiff'):
            meta = extraire_metadata_geotiff(ortho.fichier.path)
            if meta:
                if meta.get('emprise') and not ortho.emprise:
                    ortho.emprise = meta['emprise']
                if meta.get('resolution') and not ortho.resolution:
                    ortho.resolution = meta['resolution']
                ortho.largeur_px = meta.get('largeur_px')
                ortho.hauteur_px = meta.get('hauteur_px')
                ortho.systeme_proj = meta.get('systeme_proj', '')
                ortho.save()

                try:
                    generer_tuiles_locales(ortho)
                    messages.success(
                        request,
                        f'Orthophoto « {ortho.nom} » importée avec extraction automatique des métadonnées '
                        f'({ortho.largeur_px}×{ortho.hauteur_px}px, {ortho.resolution} cm/px) '
                        'et tuiles générées localement (affichage indépendant de WebODM).'
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f'Orthophoto « {ortho.nom} » importée avec métadonnées, mais la génération des '
                        f'tuiles locales a échoué ({e}). Renseignez une URL WebODM en secours si besoin.'
                    )
            else:
                messages.warning(
                    request,
                    f'Orthophoto « {ortho.nom} » importée. Métadonnées géographiques non détectées.'
                )
        else:
            messages.success(request, f'Orthophoto « {ortho.nom} » importée.')

        if mission and mission.statut == Mission.STATUT_TRAITEMENT:
            mission.statut = Mission.STATUT_TRAITEE
            mission.save(update_fields=['statut', 'date_modification'])

        if mission:
            return redirect('drones:mission_detail', pk=mission.pk)
        return redirect('drones:missions')

    return render(request, 'drones/orthophotos/import.html', {'form': form, 'mission': mission})


@login_required
@domaine_required
def orthophoto_delete(request, pk):
    ortho = get_orthophoto_by_id(pk)
    mission_pk = ortho.mission_id
    if request.method == 'POST':
        ortho.delete()
        messages.success(request, 'Orthophoto supprimée.')
        if mission_pk:
            return redirect('drones:mission_detail', pk=mission_pk)
        return redirect('drones:missions')
    return render(request, 'drones/communs/confirm_delete.html', {'obj': ortho})


@login_required
@domaine_required
def orthophoto_validate(request, pk):
    ortho = get_orthophoto_by_id(pk)
    if request.method == 'POST':
        ortho.valide = True
        ortho.date_validation = timezone.now()
        ortho.validateur = request.user
        ortho.save()
        messages.success(request, f'Orthophoto « {ortho.nom} » validée.')
    if ortho.mission_id:
        return redirect('drones:mission_detail', pk=ortho.mission_id)
    return redirect('drones:missions')


@login_required
@domaine_required
def orthophoto_integrate(request, pk):
    ortho = get_orthophoto_by_id(pk)
    if request.method == 'POST':
        if not ortho.valide:
            messages.error(request, "L'orthophoto doit être validée avant d'être intégrée à la cartographie.")
        elif not ortho.tiles_url:
            messages.error(request, "Une URL de tuiles (WebODM) est requise pour afficher l'orthophoto sur la carte.")
        else:
            if ortho.mission:
                ortho.mission.statut = Mission.STATUT_INTEGREE
                ortho.mission.save(update_fields=['statut', 'date_modification'])
            messages.success(request, f'Orthophoto « {ortho.nom} » intégrée à la cartographie principale.')
    if ortho.mission_id:
        return redirect('drones:mission_detail', pk=ortho.mission_id)
    return redirect('drones:missions')
