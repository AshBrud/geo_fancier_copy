from django.shortcuts import render
from django.db.models import Q
from foncier.models import Batiment, Espace
from foncier.serializers import BatimentSerializer, EspaceSerializer
from django.http import JsonResponse


def recherche(request):
    q = request.GET.get('q', '')
    batiments = []
    espaces = []
    if q:
        batiments = list(Batiment.objects.filter(
            Q(nom__icontains=q) | Q(code__icontains=q) |
            Q(description__icontains=q)
        ).select_related('fonction')[:10])
        espaces = list(Espace.objects.filter(
            Q(nom__icontains=q) | Q(code__icontains=q) |
            Q(usage__icontains=q)
        )[:10])
    return render(request, 'navigation/recherche.html', {
        'q': q, 'batiments': batiments, 'espaces': espaces,
        'nb_resultats': len(batiments) + len(espaces),
        'nb_batiments_campus': Batiment.objects.filter(est_actif=True).count(),
        'nb_espaces_campus': Espace.objects.count(),
        'nb_espaces_libres': Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).count(),
    })


def recherche_ajax(request):
    q = request.GET.get('q', '')
    resultats = []
    if q and len(q) >= 2:
        batiments = Batiment.objects.filter(
            Q(nom__icontains=q) | Q(code__icontains=q)
        )[:5]
        for b in batiments:
            if b.geometrie:
                centroid = b.geometrie.centroid
                resultats.append({
                    'id': b.pk, 'nom': b.nom, 'code': b.code,
                    'type': 'batiment',
                    'lat': centroid.y, 'lng': centroid.x,
                    'fonction': str(b.fonction) if b.fonction else '',
                })
        espaces = Espace.objects.filter(
            Q(nom__icontains=q) | Q(code__icontains=q)
        )[:5]
        for e in espaces:
            if e.geometrie:
                centroid = e.geometrie.centroid
                resultats.append({
                    'id': e.pk, 'nom': e.nom, 'code': e.code,
                    'type': 'espace',
                    'lat': centroid.y, 'lng': centroid.x,
                    'type_espace': e.type_espace,
                })
    return JsonResponse({'resultats': resultats})
