from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db.models import Q
from dossiers.models import Dossier, DossierMembership

User = get_user_model()


class WorkspaceFunctionalTestCase(TestCase):
    """
    Tests fonctionnels du système d'espaces de travail territoriaux (V2).
    Vérifie le cycle complet : authentification, sélection de dossier,
    routage contextuel /<slug>/... et injection du contexte dynamique.
    """

    @classmethod
    def setUpTestData(cls):
        # 1. Règle du Superuser unique : nettoyage préalable
        User.objects.filter(Q(is_superuser=True) | Q(role='superuser')).delete()

        # Création du superuser maître de test
        cls.superuser = User.objects.create_user(
            username='admin_test',
            email='admin@geofoncier.test',
            password='Password123!',
            role='superuser',
            is_staff=True,
            is_superuser=True,
        )

        # 2. Création d'un utilisateur standard
        cls.std_user = User.objects.create_user(
            username='user_test',
            email='user@geofoncier.test',
            password='Password123!',
            role='observateur',
        )

        # 3. Création de deux dossiers territoriaux (un campus et une commune)
        cls.dossier_campus = Dossier.objects.create(
            nom="Campus UAD Bambey",
            slug="campus-uad-bambey",
            type_territoire="universite",
            modules_config={
                "mod_espaces": True,
                "mod_urbanisme": True,
                "mod_drones": True,
            },
            is_active=True,
        )

        cls.dossier_commune = Dossier.objects.create(
            nom="Commune Rurale Test",
            slug="commune-rurale-test",
            type_territoire="commune",
            modules_config={
                "mod_espaces": True,
                "mod_urbanisme": False,
                "mod_drones": False,
            },
            is_active=True,
        )

        # 4. Assigner l'utilisateur standard uniquement au dossier campus
        DossierMembership.objects.create(
            user=cls.std_user,
            dossier=cls.dossier_campus,
            role='observateur',
        )

    def setUp(self):
        self.client = Client()

    def test_unauthenticated_user_redirected_to_login(self):
        """Un utilisateur anonyme doit être redirigé vers la mire de connexion."""
        response = self.client.get('/dossiers/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_superuser_can_access_dossiers_gallery(self):
        """Le Superuser a accès à la galerie globale de tous les dossiers."""
        self.client.force_login(self.superuser)
        response = self.client.get('/dossiers/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus UAD Bambey")
        self.assertContains(response, "Commune Rurale Test")

    def test_select_dossier_sets_session_and_redirects(self):
        """Sélectionner un dossier place son ID en session et redirige vers son dashboard."""
        self.client.force_login(self.superuser)
        response = self.client.get(f'/dossiers/{self.dossier_campus.slug}/select/')
        
        # Doit rediriger vers le dashboard contextuel du dossier
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/{self.dossier_campus.slug}/dashboard/')

        # La session doit mémoriser le dossier actif
        session = self.client.session
        self.assertEqual(str(session.get('active_dossier_id')), str(self.dossier_campus.id))

    def test_workspace_dashboard_renders_with_context(self):
        """Le dashboard contextuel d'un dossier actif s'affiche en 200 OK avec le bon lexique."""
        self.client.force_login(self.superuser)
        
        # Accès direct à l'URL scoped /<slug>/dashboard/
        response = self.client.get(f'/{self.dossier_campus.slug}/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # Vérification du contexte injecté par ActiveDossierMiddleware et context_processor
        self.assertIn('active_dossier', response.context)
        active_dossier = response.context['active_dossier']
        self.assertEqual(active_dossier.id, self.dossier_campus.id)

        # Lexique dynamique adapté au type d'espace (ici universite)
        self.assertIn('dossier_terms', response.context)
        terms = response.context['dossier_terms']
        self.assertIn('zone_plural', terms)

    def test_rbac_filtering_on_user_accessible_dossiers(self):
        """Un utilisateur standard ne voit que les territoires qui lui sont rattachés."""
        self.client.force_login(self.std_user)
        response = self.client.get('/dossiers/')
        self.assertEqual(response.status_code, 200)
        
        # Doit voir le campus (adhésion active) mais pas la commune
        self.assertContains(response, "Campus UAD Bambey")
        self.assertNotContains(response, "Commune Rurale Test")
