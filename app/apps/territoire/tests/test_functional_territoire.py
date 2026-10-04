from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon, MultiPolygon, LineString, MultiLineString
from django.db.models import Q
from dossiers.models import Dossier, ZoneSecteur, UniteBatie, ReseauLineaire

User = get_user_model()


def sample_multipolygon():
    p = Polygon(((14.69, -16.48), (14.69, -16.47), (14.70, -16.47), (14.70, -16.48), (14.69, -16.48)))
    return MultiPolygon(p)


def sample_multilinestring():
    line = LineString(((14.69, -16.48), (14.70, -16.47)))
    return MultiLineString(line)


class TerritoireFunctionalTestCase(TestCase):
    """
    Tests fonctionnels du module Territoire & Foncier (V2).
    Valide les vues listes, la cartographie SIG et les endpoints d'API GeoJSON.
    """

    @classmethod
    def setUpTestData(cls):
        # Règle du Superuser unique : nettoyage préalable
        User.objects.filter(Q(is_superuser=True) | Q(role='superuser')).delete()

        cls.user = User.objects.create_user(
            username='admin_test',
            email='territoire@geofoncier.test',
            password='Password123!',
            role='superuser',
            is_staff=True,
            is_superuser=True,
        )

        cls.dossier = Dossier.objects.create(
            nom="Commune Expérimentale",
            slug="commune-exp",
            type_territoire="commune",
            geometrie=sample_multipolygon(),
            is_active=True,
        )

        cls.zone = ZoneSecteur.objects.create(
            dossier=cls.dossier,
            nom="Zone Résidentielle",
            code="ZR-01",
            type_zone=ZoneSecteur.TYPE_QUARTIER,
            superficie_m2=15000.0,
            geometrie=sample_multipolygon(),
        )

        cls.bati = UniteBatie.objects.create(
            dossier=cls.dossier,
            zone_secteur=cls.zone,
            nom="Maison Familiale",
            code="BAT-001",
            superficie_m2=120.0,
            geometrie=sample_multipolygon(),
        )

        cls.reseau = ReseauLineaire.objects.create(
            dossier=cls.dossier,
            nom="Piste Principale",
            code="PST-01",
            type_voie=ReseauLineaire.TYPE_PISTE,
            longueur_metres=450.0,
            geometrie=sample_multilinestring(),
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_cartographie_view_returns_200(self):
        """La vue cartographique contextuelle s'affiche correctement."""
        response = self.client.get(f'/{self.dossier.slug}/territoire/carte/')
        self.assertEqual(response.status_code, 200)

    def test_zones_list_view_returns_200(self):
        """La vue liste des subdivisions/zones retourne 200 OK et affiche les fiches."""
        response = self.client.get(f'/{self.dossier.slug}/territoire/zones/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zone Résidentielle")
        self.assertContains(response, "ZR-01")

    def test_batiments_list_view_returns_200(self):
        """La vue liste du recensement bâti retourne 200 OK et affiche le bâti."""
        response = self.client.get(f'/{self.dossier.slug}/territoire/batiments/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maison Familiale")
        self.assertContains(response, "BAT-001")

    def test_reseaux_list_view_returns_200(self):
        """La vue liste des réseaux et voies linéaires retourne 200 OK et affiche la voirie."""
        response = self.client.get(f'/{self.dossier.slug}/territoire/reseaux/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Piste Principale")
        self.assertContains(response, "PST-01")

    def test_api_geojson_endpoints(self):
        """Les endpoints REST API GeoJSON répondent en JSON avec structure GeoJSON complète."""
        # 1. API Zones GeoJSON
        r_zones = self.client.get('/api/zones/')
        self.assertEqual(r_zones.status_code, 200)
        self.assertIn('application/json', r_zones['content-type'])
        data_zones = r_zones.json()
        self.assertEqual(data_zones['type'], 'FeatureCollection')
        self.assertTrue(any(f['properties']['code'] == 'ZR-01' for f in data_zones['features']))

        # 2. API Bâtiments GeoJSON
        r_bat = self.client.get('/api/batiments/')
        self.assertEqual(r_bat.status_code, 200)
        self.assertIn('application/json', r_bat['content-type'])
        data_bat = r_bat.json()
        self.assertEqual(data_bat['type'], 'FeatureCollection')
        self.assertTrue(any(f['properties']['code'] == 'BAT-001' for f in data_bat['features']))

        # 3. API Réseaux GeoJSON
        r_res = self.client.get('/api/reseaux/')
        self.assertEqual(r_res.status_code, 200)
        self.assertIn('application/json', r_res['content-type'])
        data_res = r_res.json()
        self.assertEqual(data_res['type'], 'FeatureCollection')
        self.assertTrue(any(f['properties']['code'] == 'PST-01' for f in data_res['features']))
