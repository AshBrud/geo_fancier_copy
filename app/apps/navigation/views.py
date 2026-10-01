from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
import json
from foncier.models import Batiment, Espace, FonctionBatiment


@login_required
def recherche(request):
    q           = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter_type', '')   # '' | 'batiment' | 'espace'
    fonction_id = request.GET.get('fonction', '')
    type_espace = request.GET.get('type_espace', '')
    statut      = request.GET.get('statut', '')         # '' | 'actif' | 'inactif'
    sort        = request.GET.get('sort', 'pertinence') # 'nom' | '-superficie'

    batiments          = []
    espaces            = []
    nb_total_batiments = 0
    nb_total_espaces   = 0

    has_filter = bool(q or fonction_id or type_espace or statut)

    if has_filter:
        # ── Bâtiments ────────────────────────────────────────────────
        if filter_type in ('', 'batiment'):
            qs_bat = Batiment.objects.select_related('fonction')
            if q:
                qs_bat = qs_bat.filter(
                    Q(nom__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q)
                )
            if fonction_id:
                qs_bat = qs_bat.filter(fonction_id=fonction_id)
            if statut == 'actif':
                qs_bat = qs_bat.filter(est_actif=True)
            elif statut == 'inactif':
                qs_bat = qs_bat.filter(est_actif=False)
            if sort == 'nom':
                qs_bat = qs_bat.order_by('nom')
            elif sort == '-superficie':
                qs_bat = qs_bat.order_by('-superficie')
            nb_total_batiments = qs_bat.count()
            batiments = list(qs_bat[:20])

        # ── Espaces ──────────────────────────────────────────────────
        if filter_type in ('', 'espace'):
            qs_esp = Espace.objects.all()
            if q:
                qs_esp = qs_esp.filter(
                    Q(nom__icontains=q) | Q(code__icontains=q) | Q(usage__icontains=q)
                )
            if type_espace:
                qs_esp = qs_esp.filter(type_espace=type_espace)
            if sort == 'nom':
                qs_esp = qs_esp.order_by('nom')
            elif sort == '-superficie':
                qs_esp = qs_esp.order_by('-superficie')
            nb_total_espaces = qs_esp.count()
            espaces = list(qs_esp[:20])

    nb_resultats = len(batiments) + len(espaces)

    # GeoJSON des résultats pour la carte (uniquement ceux qui ont une géométrie)
    features = []
    for b in batiments:
        if b.geometrie:
            features.append({
                'type': 'Feature',
                'geometry': json.loads(b.geometrie.geojson),
                'properties': {
                    'pk': b.pk, 'nom': b.nom, 'code': b.code,
                    'type': 'batiment',
                    'detail_url': f'/foncier/batiments/{b.pk}/',
                },
            })
    for e in espaces:
        if e.geometrie:
            features.append({
                'type': 'Feature',
                'geometry': json.loads(e.geometrie.geojson),
                'properties': {
                    'pk': e.pk, 'nom': e.nom, 'code': e.code,
                    'type': 'espace',
                    'couleur': e.couleur,
                    'detail_url': f'/foncier/espaces/{e.pk}/',
                },
            })
    resultats_geojson = json.dumps({'type': 'FeatureCollection', 'features': features})

    return render(request, 'navigation/recherche.html', {
        # Paramètres de la requête
        'q':           q,
        'filter_type': filter_type,
        'fonction_id': fonction_id,
        'type_espace': type_espace,
        'statut':      statut,
        'sort':        sort,
        'has_filter':  has_filter,
        # Résultats
        'batiments':          batiments,
        'espaces':            espaces,
        'nb_resultats':       nb_resultats,
        'nb_total_batiments': nb_total_batiments,
        'nb_total_espaces':   nb_total_espaces,
        'nb_resultats_total': nb_total_batiments + nb_total_espaces,
        'resultats_geojson':  resultats_geojson,
        # Données pour les filtres
        'fonctions':    list(FonctionBatiment.objects.order_by('nom')),
        'types_espace': Espace.TYPES,
        # Stats campus (hero chips)
        'nb_batiments_campus': Batiment.objects.filter(est_actif=True).count(),
        'nb_espaces_campus':   Espace.objects.count(),
        'nb_espaces_libres':   Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count(),
    })


@login_required
def recherche_ajax(request):
    q = request.GET.get('q', '').strip()
    resultats = []
    if len(q) >= 2:
        batiments = Batiment.objects.filter(
            Q(nom__icontains=q) | Q(code__icontains=q)
        ).select_related('fonction')[:7]
        for b in batiments:
            if b.geometrie:
                c = b.geometrie.centroid
                resultats.append({
                    'id':        b.pk,
                    'nom':       b.nom,
                    'code':      b.code,
                    'type':      'batiment',
                    'lat':       c.y,
                    'lng':       c.x,
                    'fonction':  str(b.fonction) if b.fonction else '',
                    'superficie': round(b.superficie) if b.superficie else None,
                    'etages':    b.etages,
                    'est_actif': b.est_actif,
                    'url':       f'/foncier/batiments/{b.pk}/',
                })
        espaces = Espace.objects.filter(
            Q(nom__icontains=q) | Q(code__icontains=q)
        )[:7]
        for e in espaces:
            if e.geometrie:
                c = e.geometrie.centroid
                resultats.append({
                    'id':         e.pk,
                    'nom':        e.nom,
                    'code':       e.code,
                    'type':       'espace',
                    'lat':        c.y,
                    'lng':        c.x,
                    'type_espace': e.type_espace,
                    'superficie': round(e.superficie) if e.superficie else None,
                    'couleur':    e.couleur,
                    'url':        f'/foncier/espaces/{e.pk}/',
                })
    return JsonResponse({'resultats': resultats})
