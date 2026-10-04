from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
import json
from dossiers.models import UniteBatie, ZoneSecteur


@login_required
def recherche(request):
    q           = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter_type', '')   # '' | 'batiment' | 'espace'
    type_espace = request.GET.get('type_espace', '')
    statut      = request.GET.get('statut', '')        # '' | 'actif' | 'inactif'
    dossier     = getattr(request, 'active_dossier', None)
    sort        = request.GET.get('sort', 'pertinence') # 'nom' | '-superficie'

    batiments          = []
    espaces            = []
    nb_total_batiments = 0
    nb_total_espaces   = 0

    has_filter = bool(q or type_espace or statut)

    if has_filter:
        # ── Bâtiments / Unités Bâties ──────────────────────────────
        if filter_type in ('', 'batiment'):
            qs_bat = UniteBatie.objects.all()
            if dossier:
                qs_bat = qs_bat.filter(dossier=dossier)
            if q:
                qs_bat = qs_bat.filter(
                    Q(nom__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q)
                )
            if statut == 'actif':
                qs_bat = qs_bat.filter(statut_occupation=UniteBatie.OCCUPATION_HABITEE)
            elif statut == 'inactif':
                qs_bat = qs_bat.exclude(statut_occupation=UniteBatie.OCCUPATION_HABITEE)
            if sort == 'nom':
                qs_bat = qs_bat.order_by('nom')
            elif sort == '-superficie':
                qs_bat = qs_bat.order_by('-superficie_m2')
            nb_total_batiments = qs_bat.count()
            batiments = list(qs_bat[:20])

        # ── Zones / Secteurs / Subdivisions ─────────────────────────
        if filter_type in ('', 'espace'):
            qs_esp = ZoneSecteur.objects.all()
            if dossier:
                qs_esp = qs_esp.filter(dossier=dossier)
            if q:
                qs_esp = qs_esp.filter(
                    Q(nom__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q)
                )
            if type_espace:
                qs_esp = qs_esp.filter(type_zone=type_espace)
            if sort == 'nom':
                qs_esp = qs_esp.order_by('nom')
            elif sort == '-superficie':
                qs_esp = qs_esp.order_by('-superficie_m2')
            nb_total_espaces = qs_esp.count()
            espaces = list(qs_esp[:20])

    nb_resultats = len(batiments) + len(espaces)

    url_prefix = f'/{dossier.slug}' if dossier else ''
    features = []
    for b in batiments:
        if b.geometrie:
            features.append({
                'type': 'Feature',
                'geometry': json.loads(b.geometrie.geojson),
                'properties': {
                    'pk': b.pk, 'nom': b.nom, 'code': b.code,
                    'type': 'batiment',
                    'detail_url': f'{url_prefix}/territoire/batiments/{b.pk}/',
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
                    'couleur': '#16A34A',
                    'detail_url': f'{url_prefix}/territoire/zones/{e.pk}/',
                },
            })
    resultats_geojson = json.dumps({'type': 'FeatureCollection', 'features': features})

    base_bat_qs = UniteBatie.objects.filter(dossier=dossier) if dossier else UniteBatie.objects.all()
    base_esp_qs = ZoneSecteur.objects.filter(dossier=dossier) if dossier else ZoneSecteur.objects.all()

    return render(request, 'navigation/recherche.html', {
        'q':           q,
        'filter_type': filter_type,
        'type_espace': type_espace,
        'statut':      statut,
        'sort':        sort,
        'has_filter':  has_filter,
        'batiments':          batiments,
        'espaces':            espaces,
        'nb_resultats':       nb_resultats,
        'nb_total_batiments': nb_total_batiments,
        'nb_total_espaces':   nb_total_espaces,
        'nb_resultats_total': nb_total_batiments + nb_total_espaces,
        'resultats_geojson':  resultats_geojson,
        'fonctions':    [],
        'types_espace': ZoneSecteur.TYPES_ZONE,
        'nb_batiments_campus': base_bat_qs.count(),
        'nb_espaces_campus':   base_esp_qs.count(),
        'nb_total_batiments_territoire': base_bat_qs.count(),
        'nb_total_zones_territoire':     base_esp_qs.count(),
        'nb_espaces_libres':   base_esp_qs.filter(type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE).count(),
        'active_dossier':      dossier,
    })


@login_required
def recherche_ajax(request):
    dossier = getattr(request, 'active_dossier', None)
    url_prefix = f'/{dossier.slug}' if dossier else ''
    q = request.GET.get('q', '').strip()
    resultats = []
    if len(q) >= 2:
        bat_qs = UniteBatie.objects.filter(dossier=dossier) if dossier else UniteBatie.objects.all()
        batiments = bat_qs.filter(
            Q(nom__icontains=q) | Q(code__icontains=q)
        )[:7]
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
                    'fonction':  b.get_usage_principal_display() if hasattr(b, 'get_usage_principal_display') else '',
                    'superficie': round(b.emprise_sol_m2) if b.emprise_sol_m2 else None,
                    'etages':    getattr(b, 'nombre_niveaux', None),
                    'est_actif': b.statut_occupation == UniteBatie.OCCUPATION_HABITEE,
                    'url':       f'{url_prefix}/territoire/batiments/{b.pk}/',
                })
        esp_qs = ZoneSecteur.objects.filter(dossier=dossier) if dossier else ZoneSecteur.objects.all()
        espaces = esp_qs.filter(
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
                    'type_espace': e.type_zone,
                    'superficie': round(e.superficie_m2) if e.superficie_m2 else None,
                    'couleur':    '#16A34A',
                    'url':        f'{url_prefix}/territoire/zones/{e.pk}/',
                })
    return JsonResponse({'resultats': resultats})
