from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.db.models import Q
from datetime import date

from dossiers.models import Dossier, ZoneSecteur, UniteBatie, ReseauLineaire
from drones.models import Mission, Orthophoto, FluxVideo
from urbanisme.models import NouvelleConstruction

User = get_user_model()


def sample_multipolygon():
    p = Polygon(((14.69, -16.48), (14.69, -16.47), (14.70, -16.47), (14.70, -16.48), (14.69, -16.48)))
    return MultiPolygon(p)


class DronesFunctionalTestCase(TestCase):
    """
    Tests fonctionnels automatisés du module Drones & Imagerie V2.
    Valide les missions de vol, les fiches détaillées, le centre de supervision en temps réel
    et les endpoints d'alimentation AJAX.
    """

    @classmethod
    def setUpTestData(cls):
        # Respecter la règle du superuser unique
        User.objects.filter(Q(is_superuser=True) | Q(role='superuser')).delete()

        cls.user = User.objects.create_user(
            username='pilote_drone_tester',
            email='drone_tester@geofoncier.test',
            password='Password123!',
            role='superuser',
            is_staff=True,
            is_superuser=True,
        )

        cls.dossier = Dossier.objects.create(
            nom="Commune de Ngom-Ngom",
            slug="commune-de-ngom-ngom",
            type_territoire="commune",
            superficie_ha=450.0,
            geometrie=sample_multipolygon(),
            is_active=True,
        )

        cls.zone = ZoneSecteur.objects.create(
            dossier=cls.dossier,
            nom="Zone d'Extension Ouest",
            code="EXT-OUEST",
            type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE,
            superficie_m2=50000.0,
            geometrie=sample_multipolygon(),
        )

        cls.bati = UniteBatie.objects.create(
            dossier=cls.dossier,
            zone_secteur=cls.zone,
            nom="Hangar Drone Base",
            code="BAT-DRONE-01",
            type_bati=UniteBatie.TYPE_ADMINISTRATIF,
            geometrie=sample_multipolygon(),
            superficie_m2=450.0,
        )

        cls.mission = Mission.objects.create(
            dossier=cls.dossier,
            nom="Mission Reconnaissance Printemps 2026",
            date_vol=date(2026, 4, 1),
            operateur="Pilote Territorial",
            drone_utilise="DJI Matrice 300 RTK",
            altitude=120.0,
            duree_minutes=42.0,
            superficie_prevue=35.0,
            statut=Mission.STATUT_ATTENTE,
            notes="Vol de reconnaissance haute résolution.",
        )

        cls.construction = NouvelleConstruction.objects.create(
            dossier=cls.dossier,
            zone_secteur=cls.zone,
            demandeur=cls.user,
            nom_projet="Station Météo Drone",
            type_construction="Station Technique",
            superficie_souhaitee=120.0,
            statut=NouvelleConstruction.STATUT_EN_COURS,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username='pilote_drone_tester', password='Password123!')
        self.client.get(f'/dossiers/{self.dossier.slug}/select/')

    def test_missions_list_view_returns_200(self):
        """La vue liste des missions de vol s'affiche correctement (200 OK) avec KPIs et contexte."""
        url = f'/{self.dossier.slug}/drones/missions/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'drones/missions/list.html')
        self.assertIn('page_obj', response.context)
        self.assertIn('creation_form', response.context)
        self.assertIn('coverage_geojson', response.context)
        self.assertContains(response, 'Mission Reconnaissance Printemps 2026')
        self.assertContains(response, 'DJI Matrice 300 RTK')

    def test_mission_create_and_lifecycle(self):
        """Création d'une mission liée au dossier actif et progression du cycle de traitement."""
        create_url = f'/{self.dossier.slug}/drones/missions/nouvelle/'
        post_data = {
            'nom': 'Mission Surveillance Sud',
            'date_vol': '2026-05-12',
            'operateur': 'Équipe SIG & Télédétection',
            'drone_utilise': 'DJI Mavic 3 Enterprise',
            'altitude': 90.0,
            'duree_minutes': 28.0,
            'superficie_prevue': 18.5,
            'notes': 'Contrôle topographique parcelles sud.',
        }
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302)

        nouvelle_mission = Mission.objects.filter(nom='Mission Surveillance Sud').first()
        self.assertIsNotNone(nouvelle_mission)
        self.assertEqual(nouvelle_mission.dossier, self.dossier)
        self.assertEqual(nouvelle_mission.statut, Mission.STATUT_ATTENTE)

        # Transition vers le statut 'En traitement'
        traitement_url = f'/{self.dossier.slug}/drones/missions/{nouvelle_mission.pk}/traitement/'
        traitement_response = self.client.post(traitement_url)
        self.assertEqual(traitement_response.status_code, 302)

        nouvelle_mission.refresh_from_db()
        self.assertEqual(nouvelle_mission.statut, Mission.STATUT_TRAITEMENT)

    def test_mission_detail_view_redirects_to_modal_in_list(self):
        """La vue détail d'une mission redirige vers la liste épurée avec ouverture automatique de la modale."""
        url = f'/{self.dossier.slug}/drones/missions/{self.mission.pk}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'?mission={self.mission.pk}', response.url)

    def test_supervision_perspectives_view_returns_200(self):
        """Le Centre de supervision temps réel s'initialise correctement (200 OK) avec les métriques territoriales."""
        url = f'/{self.dossier.slug}/drones/supervision/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'drones/supervision/perspectives.html')
        self.assertIn('dossier', response.context)
        self.assertIn('dossier_geom_json', response.context)
        self.assertIn('total_batiments', response.context)
        self.assertIn('total_reseaux', response.context)
        self.assertEqual(response.context['total_batiments'], 1)

    def test_supervision_ajax_polling_endpoint(self):
        """L'endpoint AJAX de supervision retourne un statut ok, la liste des alertes et des activités."""
        url = f'/{self.dossier.slug}/drones/perspectives/donnees/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn('alertes', data)
        self.assertIn('activites', data)
        self.assertTrue(isinstance(data['alertes'], list))
        self.assertTrue(isinstance(data['activites'], list))

    def test_orthophoto_import_page_returns_200(self):
        """La page d'import d'orthophoto s'affiche avec son formulaire."""
        url = f'/{self.dossier.slug}/drones/importer/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'drones/orthophotos/import.html')
        self.assertIn('form', response.context)
