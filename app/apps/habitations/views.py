import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .decorators import commune_edit_required, commune_view_required, signalements_required
from .forms import (ChangementStatutForm, CommuneForm, MaisonForm, PisteForm,
                    SignalementForm, VillageForm)
from .models import Commune, Maison, Notification, OrthophotoCommune, Piste, Signalement, Village

COULEUR_VILLAGE = '#0F766E'
COULEUR_MAISON = '#DC2626'
COULEUR_PISTE = '#B45309'
COULEUR_SIGNALEMENT = '#E11D48'


def _commune():
    return Commune.objects.first()


def _json_script(data):
    """JSON injecté dans un <script> : on neutralise « < » pour qu'un texte saisi
    contenant « </script> » ne puisse pas casser la page."""
    return json.dumps(data, ensure_ascii=False, default=str).replace('<', '\\u003c')


def _feature(geom, **props):
    return {'type': 'Feature', 'geometry': json.loads(geom.geojson), 'properties': props}


def _villages_annotes():
    return Village.objects.annotate(
        nb_maisons=Count('maisons'),
        nb_habitees=Count('maisons', filter=Q(maisons__statut_occupation=Maison.HABITEE)),
        surface_batie=Sum('maisons__superficie'),
    ).order_by('nom')


def _maison_feature(m):
    return _feature(m.geometrie, id=m.pk, code=m.code, village=m.village.nom,
                    superficie=m.superficie, statut=m.get_statut_occupation_display(),
                    couleur=m.couleur)


def _signalement_feature(s):
    return _feature(s.geometrie, id=s.pk, numero=s.numero, titre=s.titre,
                    categorie=s.get_categorie_display(), couleur=s.couleur, icone=s.icone,
                    statut=s.get_statut_display(), statut_code=s.statut, statut_couleur=s.statut_couleur,
                    village=s.village.nom if s.village else '—', description=s.description[:160],
                    date=s.date_signalement.strftime('%d/%m/%Y'))


def _signalements_visibles(user):
    """Le responsable communal voit tout ; un citoyen ne voit que ses propres signalements."""
    qs = Signalement.objects.select_related('village', 'auteur')
    return qs if user.can_manage_signalements else qs.filter(auteur=user)


def _couches(user, village=None, avec_maisons=False):
    """Couches cartographiques communes à toutes les cartes du module."""
    commune = _commune()
    villages = _villages_annotes()
    data = {
        'commune': _feature(commune.geometrie, nom=commune.nom) if commune else None,
        'villages': [
            _feature(v.geometrie, id=v.pk, nom=v.nom, code=v.code,
                     nb_maisons=v.nb_maisons, nb_habitees=v.nb_habitees,
                     nb_non_habitees=v.nb_maisons - v.nb_habitees,
                     surface_batie=round(v.surface_batie or 0, 2))
            for v in villages
        ],
        'pistes': [
            _feature(p.geometrie, id=p.pk, nom=str(p), type=p.get_type_voie_display(), couleur=p.couleur,
                     longueur=p.longueur)
            for p in Piste.objects.all()
        ],
        'maisons': [],
        'orthophotos': [
            {'nom': o.nom, 'tiles_url': o.tiles_url, 'zoom_min': o.zoom_min, 'zoom_max': o.zoom_max,
             'zones': o.zones()}
            for o in OrthophotoCommune.objects.exclude(tiles_url__in=['', 'en cours'])
        ],
        'signalements': [_signalement_feature(s) for s in _signalements_visibles(user)],
        'peut_voir_maisons': user.can_view_commune,
    }
    if avec_maisons and user.can_view_commune:
        qs = Maison.objects.select_related('village')
        if village:
            qs = qs.filter(village=village)
        data['maisons'] = [_maison_feature(m) for m in qs]
    return _json_script(data)


# =============================================================================
#  CARTE — cœur du système
# =============================================================================

@login_required
def carte(request):
    commune = _commune()
    ctx = {
        'commune': commune,
        'villages': Village.objects.order_by('nom'),
        'couches_json': _couches(request.user),
    }
    if commune and request.user.can_view_commune:
        ctx['stats'] = commune.stats_bati()
    if request.user.can_manage_signalements:
        ctx['stats_signalements'] = _stats_signalements(Signalement.objects.all())
    return render(request, 'habitations/carte.html', ctx)


@login_required
@commune_view_required
def api_village_maisons(request, pk):
    """Maisons d'un village, chargées à la demande quand on clique sur le village."""
    village = get_object_or_404(Village, pk=pk)
    maisons = village.maisons.select_related('village')
    return JsonResponse({
        'village': village.nom,
        'stats': village.stats_bati(),
        'maisons': {'type': 'FeatureCollection', 'features': [_maison_feature(m) for m in maisons]},
    })


@login_required
@commune_edit_required
def commune_edit(request):
    commune = _commune()
    form = CommuneForm(request.POST or None, instance=commune)
    if request.method == 'POST' and form.is_valid():
        c = form.save()
        messages.success(request, f"Limite de la commune de {c.nom} enregistrée.")
        return redirect('habitations:carte')
    return render(request, 'habitations/form.html', {
        'form': form, 'obj': commune,
        'action': 'Limite de la commune' if commune else 'Délimiter la commune de Ngogom',
        'color': '#1E3A8A', 'geom_type': 'polygon', 'back_url': 'habitations:carte',
        'couches_json': _couches(request.user),
    })


# =============================================================================
#  VILLAGES
# =============================================================================

@login_required
@commune_view_required
def villages_list(request):
    qs = _villages_annotes()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    rows = [{
        'pk': v.pk, 'nom': v.nom, 'lien': ('habitations:village_detail', v.pk),
        'cells': [v.code, v.nb_maisons, v.nb_habitees, v.nb_maisons - v.nb_habitees,
                  f"{(v.surface_batie or 0):,.2f} m²".replace(',', ' ')],
    } for v in page.object_list]
    return render(request, 'habitations/liste.html', {
        'page_obj': page, 'q': q, 'rows': rows,
        'title': 'Villages', 'icon': 'bi-houses-fill', 'color': COULEUR_VILLAGE,
        'headers': ['Identifiant', 'Maisons', 'Habitées', 'Non habitées', 'Superficie bâtie'],
        'add_label': 'Ajouter un village', 'add_url': 'habitations:village_create',
        'update_url': 'habitations:village_update', 'delete_url': 'habitations:village_delete',
        'total': Village.objects.count(), 'placeholder': 'Nom ou identifiant du village…',
    })


@login_required
@commune_view_required
def village_detail(request, pk):
    village = get_object_or_404(Village, pk=pk)
    maisons = village.maisons.all()
    return render(request, 'habitations/village_detail.html', {
        'village': village,
        'stats': village.stats_bati(),
        'maisons': maisons,
        'maison_focus': request.GET.get('maison', ''),
        'couches_json': _couches(request.user, village=village, avec_maisons=True),
    })


def _village_form(request, village, action):
    form = VillageForm(request.POST or None, instance=village)
    if request.method == 'POST' and form.is_valid():
        v = form.save()
        messages.success(request, f"Village « {v.nom} » enregistré ({v.code}).")
        return redirect('habitations:village_detail', pk=v.pk)
    return render(request, 'habitations/form.html', {
        'form': form, 'obj': village if village.pk else None, 'action': action,
        'color': COULEUR_VILLAGE, 'geom_type': 'polygon', 'back_url': 'habitations:villages',
        'couches_json': _couches(request.user),
    })


@login_required
@commune_edit_required
def village_create(request):
    commune = _commune()
    if not commune:
        return redirect('habitations:commune_edit')
    return _village_form(request, Village(commune=commune), 'Ajouter un village')


@login_required
@commune_edit_required
def village_update(request, pk):
    return _village_form(request, get_object_or_404(Village, pk=pk), 'Modifier le village')


@login_required
@commune_edit_required
def village_delete(request, pk):
    village = get_object_or_404(Village, pk=pk)
    if request.method == 'POST':
        nom = village.nom
        village.delete()
        messages.success(request, f"Village « {nom} » supprimé (avec ses maisons).")
        return redirect('habitations:villages')
    return render(request, 'territoire/confirm_delete.html', {'obj': village, 'back_url': 'habitations:villages'})


# =============================================================================
#  MAISONS
# =============================================================================

@login_required
@commune_view_required
def maisons_list(request):
    qs = Maison.objects.select_related('village')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(village__nom__icontains=q))
    statut = request.GET.get('statut', '')
    if statut:
        qs = qs.filter(statut_occupation=statut)
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    rows = [{
        'pk': m.pk, 'nom': m.code, 'lien': ('habitations:village_detail', m.village_id, f'?maison={m.pk}'),
        'cells': [m.village.nom, f"{m.superficie:,.2f} m²".replace(',', ' ') if m.superficie else '—',
                  m.get_statut_occupation_display()],
    } for m in page.object_list]
    return render(request, 'habitations/liste.html', {
        'page_obj': page, 'q': q, 'rows': rows,
        'title': 'Maisons', 'icon': 'bi-house-fill', 'color': COULEUR_MAISON,
        'headers': ['Village', 'Superficie', "Statut d'occupation"],
        'add_label': 'Ajouter une maison', 'add_url': 'habitations:maison_create',
        'update_url': 'habitations:maison_update', 'delete_url': 'habitations:maison_delete',
        'total': Maison.objects.count(), 'placeholder': 'Identifiant (M-0001) ou village…',
        'filtres': [('', 'Tous les statuts')] + Maison.STATUTS, 'filtre_actif': statut,
    })


def _maison_form(request, maison, action):
    initial = {}
    if not maison.pk and request.GET.get('village'):
        initial['village'] = request.GET['village']
    form = MaisonForm(request.POST or None, instance=maison, initial=initial)
    if request.method == 'POST' and form.is_valid():
        m = form.save()
        messages.success(request, f"Maison {m.code} enregistrée ({m.superficie:.2f} m²).")
        if 'continuer' in request.POST:
            # Saisie en série : on enchaîne sur la maison suivante du même village
            return redirect(f"{reverse('habitations:maison_create')}?village={m.village_id}")
        return redirect(f"{reverse('habitations:village_detail', args=[m.village_id])}?maison={m.pk}")
    village_id = form['village'].value()
    village = Village.objects.filter(pk=village_id).first() if village_id else None
    return render(request, 'habitations/form.html', {
        'form': form, 'obj': maison if maison.pk else None, 'action': action,
        'color': COULEUR_MAISON, 'geom_type': 'polygon', 'back_url': 'habitations:maisons',
        'couches_json': _couches(request.user, village=village, avec_maisons=True),
        'focus_village': village.pk if village else None,
        'continuer': not maison.pk,
    })


@login_required
@commune_edit_required
def maison_create(request):
    return _maison_form(request, Maison(), 'Ajouter une maison')


@login_required
@commune_edit_required
def maison_update(request, pk):
    return _maison_form(request, get_object_or_404(Maison, pk=pk), 'Modifier la maison')


@login_required
@commune_edit_required
def maison_delete(request, pk):
    m = get_object_or_404(Maison, pk=pk)
    if request.method == 'POST':
        village_id = m.village_id
        m.delete()
        messages.success(request, f"Maison {m.code} supprimée.")
        return redirect('habitations:village_detail', pk=village_id)
    return render(request, 'territoire/confirm_delete.html', {'obj': m, 'back_url': 'habitations:maisons'})


# =============================================================================
#  ROUTES ET PISTES
# =============================================================================

@login_required
@commune_view_required
def pistes_list(request):
    qs = Piste.objects.all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(nom__icontains=q)
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    rows = [{
        'pk': p.pk, 'nom': str(p), 'lien': ('habitations:piste_update', p.pk),
        'cells': [p.get_type_voie_display(), f"{(p.longueur or 0) / 1000:.2f} km"],
    } for p in page.object_list]
    return render(request, 'habitations/liste.html', {
        'page_obj': page, 'q': q, 'rows': rows,
        'title': 'Routes et pistes', 'icon': 'bi-signpost-split-fill', 'color': COULEUR_PISTE,
        'headers': ['Type', 'Longueur'],
        'add_label': 'Tracer une route / piste', 'add_url': 'habitations:piste_create',
        'update_url': 'habitations:piste_update', 'delete_url': 'habitations:piste_delete',
        'total': Piste.objects.count(), 'placeholder': 'Nom du tronçon…',
    })


def _piste_form(request, piste, action):
    form = PisteForm(request.POST or None, instance=piste)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Tracé enregistré.")
        return redirect('habitations:pistes')
    return render(request, 'habitations/form.html', {
        'form': form, 'obj': piste if piste.pk else None, 'action': action,
        'color': COULEUR_PISTE, 'geom_type': 'line', 'back_url': 'habitations:pistes',
        'couches_json': _couches(request.user),
    })


@login_required
@commune_edit_required
def piste_create(request):
    return _piste_form(request, Piste(), 'Tracer une route / piste')


@login_required
@commune_edit_required
def piste_update(request, pk):
    return _piste_form(request, get_object_or_404(Piste, pk=pk), 'Modifier le tracé')


@login_required
@commune_edit_required
def piste_delete(request, pk):
    p = get_object_or_404(Piste, pk=pk)
    if request.method == 'POST':
        p.delete()
        messages.success(request, "Tracé supprimé.")
        return redirect('habitations:pistes')
    return render(request, 'territoire/confirm_delete.html', {'obj': p, 'back_url': 'habitations:pistes'})


# =============================================================================
#  SIGNALEMENTS
# =============================================================================

def _stats_signalements(qs):
    agg = qs.aggregate(
        total=Count('id'),
        nouveaux=Count('id', filter=Q(statut=Signalement.NOUVEAU)),
        pris_en_charge=Count('id', filter=Q(statut=Signalement.PRIS_EN_CHARGE)),
        en_cours=Count('id', filter=Q(statut=Signalement.EN_COURS)),
        resolus=Count('id', filter=Q(statut=Signalement.RESOLU)),
    )
    return agg


@login_required
def signalement_create(request):
    form = SignalementForm(request.POST or None, request.FILES or None,
                           initial={'village': request.user.village_id})
    if request.method == 'POST' and form.is_valid():
        s = form.save(commit=False)
        s.auteur = request.user
        s.save()
        nb_notifies = s.publier()
        if nb_notifies:
            dest = 'responsables communaux' if nb_notifies > 1 else 'responsable communal'
            messages.success(request, f"Merci ! Votre signalement {s.numero} a été transmis "
                                      f"et notifié à {nb_notifies} {dest}.")
        else:
            messages.warning(request, f"Signalement {s.numero} enregistré, mais aucun autre responsable n'a été "
                                      "notifié : il a été créé depuis un compte responsable. Pour qu'un "
                                      "administrateur reçoive une notification, le signalement doit être fait "
                                      "depuis le compte de la personne qui signale.")
        return redirect('habitations:signalement_detail', pk=s.pk)
    return render(request, 'habitations/signalement_form.html', {
        'form': form,
        'couches_json': _couches(request.user),
    })


@login_required
def signalements(request):
    """Tableau de bord des signalements. Le responsable communal voit tout,
    un citoyen ne voit que les siens (« Mes signalements »)."""
    base = _signalements_visibles(request.user)
    qs = base
    statut = request.GET.get('statut', '')
    categorie = request.GET.get('categorie', '')
    if statut:
        qs = qs.filter(statut=statut)
    if categorie:
        qs = qs.filter(categorie=categorie)
    page = Paginator(qs, 15).get_page(request.GET.get('page'))
    return render(request, 'habitations/signalements.html', {
        'page_obj': page,
        'stats': _stats_signalements(base),
        'statut': statut, 'categorie': categorie,
        'statuts': Signalement.STATUTS, 'categories': Signalement.CATEGORIES,
        'couches_json': _couches(request.user),
        'titre': 'Signalements communaux' if request.user.can_manage_signalements else 'Mes signalements',
    })


@login_required
def signalement_detail(request, pk):
    s = get_object_or_404(Signalement.objects.select_related('village', 'auteur'), pk=pk)
    if not (request.user.can_manage_signalements or s.auteur_id == request.user.pk):
        raise Http404
    form = None
    if request.user.can_manage_signalements and s.statuts_suivants():
        form = ChangementStatutForm(s, request.POST or None)
        if request.method == 'POST' and form.is_valid():
            try:
                s.changer_statut(form.cleaned_data['nouveau_statut'], request.user,
                                 form.cleaned_data['commentaire'])
                messages.success(request, f"{s.numero} : statut passé à « {s.get_statut_display()} ».")
            except ValidationError as e:
                messages.error(request, e.messages[0])
            return redirect('habitations:signalement_detail', pk=s.pk)
    return render(request, 'habitations/signalement_detail.html', {
        's': s,
        'historique': s.historique.select_related('utilisateur'),
        'form': form,
        'etapes': Signalement.STATUTS,
        'etape_index': [c for c, _ in Signalement.STATUTS].index(s.statut),
        'couches_json': _couches(request.user),
    })


# =============================================================================
#  NOTIFICATIONS
# =============================================================================

@login_required
def notifications(request):
    qs = request.user.notifications_commune.select_related('signalement')
    if request.method == 'POST':
        qs.filter(lue=False).update(lue=True)
        messages.success(request, "Toutes les notifications ont été marquées comme lues.")
        return redirect('habitations:notifications')
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    return render(request, 'habitations/notifications.html', {'page_obj': page})


@login_required
def notification_ouvrir(request, pk):
    """Marque la notification comme lue et ouvre directement le signalement localisé."""
    n = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    if not n.lue:
        n.lue = True
        n.save(update_fields=['lue'])
    return redirect('commune:signalement_detail', pk=n.signalement_id)
