import os
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.management.base import CommandError
from accounts.decorators import domaine_required
from territoire.models import Batiment
from territoire.forms import BatimentForm, BatimentImportForm
from territoire.selectors import (
    get_batiments_queryset,
    get_batiment_by_id,
    get_batiments_stats,
    get_espaces_libres_geojson,
)


@login_required
def batiments_list(request):
    """
    Répertoire exhaustif du patrimoine bâti :
    Grille enrichie avec intégration SlideOver au clic et modale d'ajout direct (Zero-Page Create).
    """
    q = request.GET.get('q', '')

    # Traitement soumission directe de la modale de création
    if request.method == 'POST' and 'submit_batiment' in request.POST:
        if not (request.user.is_domaine_foncier or request.user.is_admin):
            messages.error(request, "Accès refusé. Privilèges insuffisants pour créer un bâtiment.")
            return redirect('territoire:batiments')
        creation_form = BatimentForm(request.POST, request.FILES)
        if creation_form.is_valid():
            bat = creation_form.save()
            messages.success(request, f"Bâtiment « {bat.nom} » enregistré avec succès.")
            return redirect('territoire:batiments')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire du bâtiment.")
    else:
        creation_form = BatimentForm()

    qs = get_batiments_queryset(q=q)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    stats = get_batiments_stats()

    context = {
        'page_obj': page,
        'q': q,
        'total_batiments': stats['total'],
        'nb_actifs': stats['actifs'],
        'superficie_totale': stats['superficie_totale'],
        'superficie_ha': stats['superficie_ha'],
        'creation_form': creation_form,
        'espaces_libres_json': get_espaces_libres_geojson(),
    }
    return render(request, 'territoire/batiments_list.html', context)


@login_required
def batiment_detail(request, pk):
    batiment = get_object_or_404(Batiment, pk=pk)
    return render(request, 'territoire/batiment_detail.html', {'batiment': batiment})


@login_required
@domaine_required
def batiment_create(request):
    form = BatimentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        bat = form.save()
        messages.success(request, f'Bâtiment « {bat.nom} » créé avec succès.')
        return redirect('territoire:batiments')
    return render(request, 'territoire/batiment_form.html', {
        'form': form,
        'action': 'Ajouter un bâtiment',
        'obj': None,
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def batiment_update(request, pk):
    bat = get_object_or_404(Batiment, pk=pk)
    form = BatimentForm(request.POST or None, request.FILES or None, instance=bat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Bâtiment « {bat.nom} » modifié.')
        return redirect('territoire:batiments')
    return render(request, 'territoire/batiment_form.html', {
        'form': form,
        'action': 'Modifier le bâtiment',
        'obj': bat,
        'espaces_libres_json': get_espaces_libres_geojson(),
    })


@login_required
@domaine_required
def batiment_delete(request, pk):
    bat = get_object_or_404(Batiment, pk=pk)
    if request.method == 'POST':
        nom = bat.nom
        bat.delete()
        messages.success(request, f'Bâtiment « {nom} » supprimé.')
        return redirect('territoire:batiments')
    return render(request, 'territoire/confirm_delete.html', {
        'obj': bat, 'type': 'le bâtiment', 'back_url': 'territoire:batiments'
    })


@login_required
@domaine_required
def batiment_import_sig(request):
    from territoire.management.commands._sig_import import sync_batiments

    form = BatimentImportForm(request.POST or None, request.FILES or None)
    resultat = None

    if request.method == 'POST' and form.is_valid():
        fichier = form.cleaned_data['fichier']
        suffix = os.path.splitext(fichier.name)[1] or '.geojson'
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            for chunk in fichier.chunks():
                tmp.write(chunk)
            tmp.close()
            resultat = sync_batiments(
                tmp.name,
                source_crs=form.cleaned_data.get('source_crs') or None,
                dry_run=form.cleaned_data['dry_run'],
            )
            if resultat['created'] or resultat['updated']:
                verbe = 'Prévisualisation' if form.cleaned_data['dry_run'] else 'Import'
                messages.success(
                    request,
                    f"{verbe} terminé(e) : {resultat['created']} créé(s), "
                    f"{resultat['updated']} mis à jour, {resultat['skipped']} ignoré(s)."
                )
            else:
                messages.warning(request, "Aucun bâtiment valide trouvé dans ce fichier.")
        except CommandError as exc:
            messages.error(request, str(exc))
        finally:
            os.unlink(tmp.name)

    return render(request, 'territoire/batiment_import_sig.html', {
        'form': form,
        'resultat': resultat,
    })
