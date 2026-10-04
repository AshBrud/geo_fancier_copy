from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Sum, Count, Q
from dossiers.models import ZoneSecteur, UniteBatie, ReseauLineaire
from .serializers import (
    ZoneSecteurSerializer, UniteBatieSerializer, ReseauLineaireSerializer,
)


class ZoneSecteurAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dossier_id = request.GET.get('dossier_id') or request.session.get('active_dossier_id')
        zones = ZoneSecteur.objects.all()
        if dossier_id:
            zones = zones.filter(dossier_id=dossier_id)
        type_filter = request.GET.get('type')
        if type_filter:
            zones = zones.filter(type_zone=type_filter)
        serializer = ZoneSecteurSerializer(zones, many=True)
        return Response(serializer.data)


class UniteBatieAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dossier_id = request.GET.get('dossier_id') or request.session.get('active_dossier_id')
        batiments = UniteBatie.objects.filter(est_actif=True)
        if dossier_id:
            batiments = batiments.filter(dossier_id=dossier_id)
        q = request.GET.get('q')
        if q:
            batiments = batiments.filter(Q(nom__icontains=q) | Q(code__icontains=q))
        serializer = UniteBatieSerializer(batiments, many=True)
        return Response(serializer.data)


class ReseauLineaireAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dossier_id = request.GET.get('dossier_id') or request.session.get('active_dossier_id')
        reseaux = ReseauLineaire.objects.all()
        if dossier_id:
            reseaux = reseaux.filter(dossier_id=dossier_id)
        serializer = ReseauLineaireSerializer(reseaux, many=True)
        return Response(serializer.data)


class StatsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dossier_id = request.GET.get('dossier_id')
        zones_qs = ZoneSecteur.objects.all()
        batiments_qs = UniteBatie.objects.all()
        reseaux_qs = ReseauLineaire.objects.all()
        if dossier_id:
            zones_qs = zones_qs.filter(dossier_id=dossier_id)
            batiments_qs = batiments_qs.filter(dossier_id=dossier_id)
            reseaux_qs = reseaux_qs.filter(dossier_id=dossier_id)

        zones_stats = zones_qs.values('type_zone').annotate(
            count=Count('id'),
            superficie=Sum('superficie_m2')
        )
        stats = {item['type_zone']: {
            'count': item['count'],
            'superficie': item['superficie'] or 0
        } for item in zones_stats}

        total_superficie = zones_qs.aggregate(t=Sum('superficie_m2'))['t'] or 0
        superficie_batiments = batiments_qs.aggregate(t=Sum('superficie_m2'))['t'] or 0
        longueur_reseaux = reseaux_qs.aggregate(t=Sum('longueur_metres'))['t'] or 0

        return Response({
            'total_zones': zones_qs.count(),
            'total_batiments': batiments_qs.count(),
            'total_reseaux': reseaux_qs.count(),
            'superficie_totale_m2': total_superficie,
            'superficie_batiments_m2': superficie_batiments,
            'longueur_reseaux_m': longueur_reseaux,
            'par_type_zone': stats,
        })


class OrthophotoAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from drones.models import Orthophoto, Mission

        orthos = Orthophoto.objects.filter(
            tiles_url__gt='',
            valide=True,
        ).filter(
            Q(mission__isnull=True) | Q(mission__statut=Mission.STATUT_INTEGREE)
        ).order_by('-date_prise').values('id', 'nom', 'date_prise', 'tiles_url', 'operateur')

        data = [
            {**o, 'date_prise': o['date_prise'].isoformat() if o['date_prise'] else None}
            for o in orthos
        ]
        return Response(data)
