from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.db.models import Q
from dossiers.models import Dossier, DossierMembership, ZoneSecteur, UniteBatie

User = get_user_model()


def sample_multipolygon():
    p = Polygon(((14.69, -16.48), (14.69, -16.47), (14.70, -16.47), (14.70, -16.48), (14.69, -16.48)))
    return MultiPolygon(p)


class DashboardFunctionalTestCase(TestCase):
    """
    Tests fonctionnels du Tableau de Bord Unifié (V2).
    Vérifie le rendu unifié des indicateurs clés (KPI), l'absence d'erreurs 500
    et le comportement de routage contextuel.
    """

    @classmethod
    def setUpTestData(cls):
        # Règle du Superuser unique : nettoyage préalable
        User.objects.filter(Q(is_superuser=True) | Q(role='superuser')).delete()

        cls.user = User.objects.create_user(
            username='admin_test',
            email='tester@geofoncier.test',
            password='Password123!',
            role='superuser',
            is_staff=True,
            is_superuser=True,
        )

        cls.dossier = Dossier.objects.create(
            nom="Territoire de Démonstration",
            slug="territoire-demo",
            type_territoire="commune",
            superficie_ha=120.5,
            geometrie=sample_multipolygon(),
            is_active=True,
        )

        # Création d'objets fonciers pour tester le calcul des KPI
        cls.zone = ZoneSecteur.objects.create(
            dossier=cls.dossier,
            nom="Secteur Nord",
            code="SEC-NORD",
            type_zone=ZoneSecteur.TYPE_QUARTIER,
            superficie_m2=50000.0,
            geometrie=sample_multipolygon(),
        )

        cls.bati = UniteBatie.objects.create(
            dossier=cls.dossier,
            zone_secteur=cls.zone,
            nom="Bâtiment Administratif",
            code="BAT-ADM-01",
            superficie_m2=450.0,
            geometrie=sample_multipolygon(),
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_root_url_redirects_or_renders_dashboard(self):
        """La racine '/' redirige vers le dashboard ou la galerie de dossiers."""
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])

    def test_contextual_dashboard_returns_200(self):
        """L'accès à /<slug>/dashboard/ retourne 200 OK avec le template unifié."""
        response = self.client.get(f'/{self.dossier.slug}/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')
        self.assertContains(response, "Territoire de Démonstration")

    def test_dashboard_context_metrics(self):
        """Vérifie que les métriques territoriales sont correctement calculées et transmises."""
        response = self.client.get(f'/{self.dossier.slug}/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        ctx = response.context
        self.assertIn('total_batiments', ctx)
        self.assertEqual(ctx['total_batiments'], 1)
        self.assertIn('total_espaces', ctx)
        self.assertEqual(ctx['total_espaces'], 1)
        # La superficie totale est calculée automatiquement par PostGIS en projection UTM 28N
        self.assertEqual(ctx['superficie_totale'], 152.74)

    def test_dashboard_html_renders_exact_kpis_and_data(self):
        """Vérifie que les KPI, graphiques et données réelles sont physiquement inscrits dans le HTML."""
        response = self.client.get(f'/{self.dossier.slug}/dashboard/')
        self.assertEqual(response.status_code, 200)

        # 1. Présence du nom du territoire et des KPI calculés par PostGIS
        self.assertContains(response, "Territoire de Démonstration")
        self.assertContains(response, "152")
        self.assertContains(response, "Superficie totale (ha)")

        # 2. Présence du lexique contextuel appliqué à la commune
        self.assertContains(response, "Villages &amp; Quartiers")
        self.assertContains(response, "Concessions")
        self.assertContains(response, "routes &amp; pistes rurales")

        # 3. Présence du volet d'administration institutionnelle (Superuser)
        self.assertContains(response, "Journal des activités")

        # 4. Présence des scripts d'initialisation des graphiques Donut
        self.assertContains(response, "Espace libre")
        self.assertContains(response, "espaceChart")
