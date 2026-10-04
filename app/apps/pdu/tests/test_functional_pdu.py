from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.db.models import Q
from dossiers.models import Dossier, ZoneSecteur, UniteBatie

User = get_user_model()


def sample_multipolygon():
    p = Polygon(((14.69, -16.48), (14.69, -16.47), (14.70, -16.47), (14.70, -16.48), (14.69, -16.48)))
    return MultiPolygon(p)


class PduFunctionalTestCase(TestCase):
    """
    Tests fonctionnels du module PDU (Plan de Développement Urbain) V2.
    Vérifie le rendu sans erreur des statistiques foncières et la compilation des templates.
    """

    @classmethod
    def setUpTestData(cls):
        User.objects.filter(Q(is_superuser=True) | Q(role='superuser')).delete()

        cls.user = User.objects.create_user(
            username='admin_pdu_test',
            email='pdu_tester@geofoncier.test',
            password='Password123!',
            role='superuser',
            is_staff=True,
            is_superuser=True,
        )

        cls.dossier = Dossier.objects.create(
            nom="Commune de Ngom-Ngom",
            slug="commune-de-ngom-ngom",
            type_territoire="commune",
            superficie_ha=200.0,
            geometrie=sample_multipolygon(),
            is_active=True,
        )

        cls.zone = ZoneSecteur.objects.create(
            dossier=cls.dossier,
            nom="Centre Bourg",
            code="CB-01",
            type_zone=ZoneSecteur.TYPE_VILLAGE,
            superficie_m2=30000.0,
            geometrie=sample_multipolygon(),
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_pdu_statistiques_view_returns_200(self):
        """L'accès à /<slug>/pdu/ rend le template pdu/statistiques.html en 200 OK."""
        response = self.client.get(f'/{self.dossier.slug}/pdu/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pdu/statistiques.html')
        self.assertContains(response, "Statistiques Foncières")
        self.assertContains(response, "Commune de Ngom-Ngom")
