import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from territoire.models import (
    Espace, Batiment, Terrain, EspaceVert, Voirie, PointInteret, Campus,
)
from drones.models import Orthophoto, Mission


@login_required
def cartographie(request):
    """
    Système d'Information Géographique interactif du territoire :
    Superpose les orthophotos validées, les emprises du bâti, les parcelles,
    les espaces libres/réservés et le réseau viaire.
    """
    ortho_qs = (
        Orthophoto.objects.filter(
            tiles_url__gt='',
            valide=True,
        )
        .filter(Q(mission__isnull=True) | Q(mission__statut=Mission.STATUT_INTEGREE))
        .order_by('-date_prise')
    )
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
    campus = Campus.objects.first()
    return render(request, 'cartographie/map.html', {
        'orthophotos_json': json.dumps(orthos, ensure_ascii=False, default=str),
        'nb_orthophotos': len(orthos),
        'total_espaces': Espace.objects.count(),
        'nb_espaces_libres': Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count(),
        'nb_espaces_reserves': Espace.objects.filter(type_espace=Espace.TYPE_RESERVE).count(),
        'nb_espaces_occupes': Espace.objects.filter(type_espace=Espace.TYPE_OCCUPE).count(),
        'total_batiments': Batiment.objects.filter(est_actif=True).count(),
        'nb_terrains': Terrain.objects.exclude(type_terrain__icontains='sport').count(),
        'nb_terrains_sportifs': Terrain.objects.filter(type_terrain__icontains='sport').count(),
        'nb_espaces_verts': EspaceVert.objects.count(),
        'nb_voiries': Voirie.objects.count(),
        'nb_points_interet': PointInteret.objects.count(),
        'campus': campus,
        'campus_geom_json': campus.geometrie.geojson if campus and campus.geometrie else 'null',
    })
