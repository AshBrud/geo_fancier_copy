import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from dossiers.models import ZoneSecteur, UniteBatie, ReseauLineaire
from drones.models import Orthophoto, Mission


@login_required
def cartographie(request):
    """
    Système d'Information Géographique interactif du territoire :
    Superpose les orthophotos validées, les emprises du bâti, les subdivisions territoriales
    et le réseau linéaire/viaire.
    """
    dossier = getattr(request, 'active_dossier', None)

    ortho_qs = (
        Orthophoto.objects.filter(
            tiles_url__gt='',
            valide=True,
        )
        .filter(Q(mission__isnull=True) | Q(mission__statut=Mission.STATUT_INTEGREE))
        .order_by('-date_prise')
    )
    if dossier:
        ortho_qs = ortho_qs.filter(Q(mission__dossier=dossier) | Q(mission__isnull=True))

    orthos = [
        {
            'id': o.id,
            'nom': o.nom,
            'date_prise': o.date_prise,
            'tiles_url': o.tiles_url,
            'operateur': o.operateur,
            'bounds': o.emprise.extent if o.emprise else None,
            'date_mission': o.date_prise.strftime('%d/%m/%Y') if o.date_prise else '',
        }
        for o in ortho_qs
    ]

    zones_qs = ZoneSecteur.objects.all()
    batiments_qs = UniteBatie.objects.all()
    reseaux_qs = ReseauLineaire.objects.all()
    if dossier:
        zones_qs = zones_qs.filter(dossier=dossier)
        batiments_qs = batiments_qs.filter(dossier=dossier)
        reseaux_qs = reseaux_qs.filter(dossier=dossier)

    dossier_geom_json = dossier.geometrie.geojson if dossier and dossier.geometrie else 'null'

    return render(request, 'cartographie/map.html', {
        'orthophotos_json': json.dumps(orthos, ensure_ascii=False, default=str),
        'nb_orthophotos': len(orthos),
        'total_zones': zones_qs.count(),
        'total_espaces': zones_qs.count(),
        'nb_espaces_libres': zones_qs.filter(type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE).count(),
        'nb_espaces_reserves': zones_qs.filter(type_zone=ZoneSecteur.TYPE_ESPACE_RESERVE).count(),
        'total_batiments': batiments_qs.count(),
        'total_reseaux': reseaux_qs.count(),
        'nb_voiries': reseaux_qs.count(),
        'nb_terrains': 0,
        'nb_terrains_sportifs': 0,
        'nb_espaces_verts': 0,
        'nb_points_interet': 0,
        'dossier': dossier,
        'dossier_geom_json': dossier_geom_json,
        'campus': dossier,
        'campus_geom_json': dossier_geom_json,
    })
