from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Sum, Count
from .models import Espace, Batiment
from .serializers import EspaceSerializer, BatimentSerializer


class EspaceAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        espaces = Espace.objects.all()
        type_filter = request.GET.get('type')
        if type_filter:
            espaces = espaces.filter(type_espace=type_filter)
        serializer = EspaceSerializer(espaces, many=True)
        return Response(serializer.data)


class BatimentAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        batiments = Batiment.objects.filter(est_actif=True)
        q = request.GET.get('q')
        if q:
            from django.db.models import Q
            batiments = batiments.filter(Q(nom__icontains=q) | Q(code__icontains=q))
        serializer = BatimentSerializer(batiments, many=True)
        return Response(serializer.data)


class StatsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        espaces_stats = Espace.objects.values('type_espace').annotate(
            count=Count('id'),
            superficie=Sum('superficie')
        )
        stats = {item['type_espace']: {
            'count': item['count'],
            'superficie': item['superficie'] or 0
        } for item in espaces_stats}

        total_superficie = Espace.objects.aggregate(t=Sum('superficie'))['t'] or 0
        superficie_batiments = Batiment.objects.aggregate(t=Sum('superficie'))['t'] or 0

        return Response({
            'total_espaces': Espace.objects.count(),
            'total_batiments': Batiment.objects.count(),
            'superficie_totale': total_superficie,
            'superficie_batiments': superficie_batiments,
            'taux_occupation': round(
                (stats.get('occupe', {}).get('superficie', 0) / total_superficie * 100)
                if total_superficie else 0, 1
            ),
            'par_type': stats,
        })
