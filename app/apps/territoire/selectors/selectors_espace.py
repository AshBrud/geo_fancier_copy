import json
from django.db.models import Q, Sum, Count
from territoire.models import Espace, Batiment
from urbanisme.models import NouvelleConstruction as NC


def get_espaces_queryset(q: str = '', type_filter: str = '', sort: str = 'nom'):
    """Retourne le queryset ordonné et filtré des sous-espaces fonciers."""
    qs = Espace.objects.select_related('campus').all()
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(code__icontains=q))
    if type_filter:
        qs = qs.filter(type_espace=type_filter)

    valid_sorts = {'nom', '-nom', 'code', '-code', 'superficie', '-superficie'}
    return qs.order_by(sort if sort in valid_sorts else 'nom')


def get_espace_by_id(pk: int):
    """Résout un espace foncier par sa clé primaire."""
    return Espace.objects.filter(pk=pk).select_related('campus').first()


def get_espaces_libres_geojson():
    """Génère le FeatureCollection GeoJSON des espaces libres pour l'aide au positionnement."""
    espaces = []
    for espace in Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).order_by('nom'):
        if not espace.geometrie:
            continue
        espaces.append({
            'type': 'Feature',
            'geometry': json.loads(espace.geometrie.geojson),
            'properties': {
                'id': espace.pk,
                'code': espace.code,
                'nom': espace.nom,
                'superficie': espace.superficie,
            },
        })
    return json.dumps(espaces, ensure_ascii=False)


def get_espaces_stats_globales():
    """Calcule les agrégats de superficie et saturation sur l'ensemble des sous-espaces."""
    stats = {
        t[0]: Espace.objects.filter(type_espace=t[0]).aggregate(count=Count('id'), total=Sum('superficie'))
        for t in Espace.TYPES
    }
    total_espaces = Espace.objects.count()
    total_superficie = Espace.objects.aggregate(s=Sum('superficie'))['s'] or 0.0

    espaces_actifs = list(Espace.objects.filter(
        type_espace__in=[Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE]
    ))
    sup_constructible_totale = sum(
        (e.superficie or 0) * (e.taux_occupation / 100) for e in espaces_actifs
    )

    pks_allouees = set()
    pks_allouees_libres = set()
    for e in espaces_actifs:
        pks = NC.pks_pour_espace(e)
        pks_allouees.update(pks)
        if e.type_espace == Espace.TYPE_LIBRE:
            pks_allouees_libres.update(pks)

    sup_allouee_totale = sum(
        c.superficie_souhaitee or 0 for c in NC.objects.filter(pk__in=pks_allouees)
    ) if pks_allouees else 0.0

    sup_allouee_libre = sum(
        c.superficie_souhaitee or 0 for c in NC.objects.filter(pk__in=pks_allouees_libres)
    ) if pks_allouees_libres else 0.0

    sup_occupee_par_espace = {
        e.pk: e.superficie_batie + e.superficie_terrains + e.superficie_espaces_verts
        for e in espaces_actifs
    }
    sup_batie_totale = sum(sup_occupee_par_espace.values())
    sup_batie_libre = sum(
        sup_occupee_par_espace[e.pk] for e in espaces_actifs if e.type_espace == Espace.TYPE_LIBRE
    )

    if Espace.TYPE_LIBRE in stats:
        stats[Espace.TYPE_LIBRE]['total'] = max(
            0.0, (stats[Espace.TYPE_LIBRE]['total'] or 0) - sup_allouee_libre - sup_batie_libre
        )

    sup_constructible_nette = max(
        0.0, sup_constructible_totale - sup_allouee_totale - sup_batie_totale
    )

    # Nombre d'espaces saturés (taux >= 80%)
    nb_espaces_satures = sum(
        1 for e in espaces_actifs
        if NC.bilan_espace(e)['constructible'] > 0 and (NC.bilan_espace(e)['occupee'] / NC.bilan_espace(e)['constructible']) >= 0.80
    )

    return {
        'stats': stats,
        'total_espaces': total_espaces,
        'total_superficie': total_superficie,
        'sup_constructible_totale': sup_constructible_totale,
        'sup_constructible_nette': sup_constructible_nette,
        'nb_espaces_satures': nb_espaces_satures,
    }


def enrich_espace_capacite(espace):
    """Calcule le bilan de constructibilité et d'affectation pour un espace donné."""
    if espace.type_espace not in (Espace.TYPE_LIBRE, Espace.TYPE_OCCUPE):
        return {
            'cap_constructible': None,
            'cap_engagee': None,
            'cap_nette': None,
            'cap_pct': 0,
            'cap_niveau': 'secondary',
        }

    bilan = NC.bilan_espace(espace)
    pct = bilan['pct']
    niveau = 'danger' if pct >= 80 else ('warning' if pct >= 50 else 'success')

    return {
        'cap_constructible': round(bilan['constructible']),
        'cap_engagee': round(bilan['allouee']),
        'cap_nette': round(bilan['nette']),
        'cap_pct': pct,
        'cap_niveau': niveau,
    }
