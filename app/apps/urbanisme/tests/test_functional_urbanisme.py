from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.db.models import Q
from datetime import date

from dossiers.models import Dossier, ZoneSecteur, UniteBatie
from urbanisme.models import NouvelleConstruction, HistoriqueConstruction

User = get_user_model()


def sample_multipolygon():
    p = Polygon(((14.69, -16.48), (14.69, -16.47), (14.70, -16.47), (14.70, -16.48), (14.69, -16.48)))
    return MultiPolygon(p)


class UrbanismeFunctionalTestCase(TestCase):
    """
    Tests fonctionnels du module Urbanisme & Faisabilité V2.
    Valide les vues listes, la simulation cartographique, le moteur d'aide à la décision
    et le cycle de vie des demandes d'implantation.
    """

    @classmethod
    def setUpTestData(cls):
        User.objects.filter(Q(is_superuser=True) | Q(role='superuser')).delete()

        cls.user = User.objects.create_user(
            username='admin_urbanisme_test',
            email='urba_tester@geofoncier.test',
            password='Password123!',
            role='superuser',
            is_staff=True,
            is_superuser=True,
        )

        cls.dossier = Dossier.objects.create(
            nom="Commune de Ngom-Ngom",
            slug="commune-de-ngom-ngom",
            type_territoire="commune",
            superficie_ha=300.0,
            geometrie=sample_multipolygon(),
            is_active=True,
        )

        cls.zone = ZoneSecteur.objects.create(
            dossier=cls.dossier,
            nom="Secteur Est",
            code="SEC-EST",
            type_zone=ZoneSecteur.TYPE_ESPACE_LIBRE,
            superficie_m2=60000.0,
            geometrie=sample_multipolygon(),
        )

        cls.bati = UniteBatie.objects.create(
            dossier=cls.dossier,
            zone_secteur=cls.zone,
            nom="Bâtiment Pilote",
            code="BAT-PLT-01",
            superficie_m2=250.0,
            geometrie=sample_multipolygon(),
        )

        cls.projet = NouvelleConstruction.objects.create(
            dossier=cls.dossier,
            zone_secteur=cls.zone,
            nom_projet="Centre de Santé Communal",
            type_construction="Équipement de santé",
            superficie_souhaitee=1200.0,
            demandeur=cls.user,
            statut=NouvelleConstruction.STATUT_EN_COURS,
        )

        cls.historique = HistoriqueConstruction.objects.create(
            unite_batie=cls.bati,
            type_travaux=HistoriqueConstruction.TYPE_CONSTRUCTION,
            date_debut=date(2025, 1, 15),
            description="Travaux de fondation et gros œuvre",
            cout=15000000.0,
            maitre_ouvrage="Entreprise BTP Sénégal",
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_constructions_list_view_returns_200(self):
        """La vue liste des projets de construction retourne 200 OK et affiche les projets."""
        response = self.client.get(f'/{self.dossier.slug}/urbanisme/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'urbanisme/constructions/list.html')
        self.assertContains(response, "Centre de Santé Communal")
        self.assertContains(response, "Équipement de santé")

    def test_faisabilite_simulation_view_returns_200(self):
        """La vue de simulation spatiale / faisabilité retourne 200 OK avec le formulaire."""
        response = self.client.get(f'/{self.dossier.slug}/urbanisme/faisabilite/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'urbanisme/constructions/simulation.html')
        self.assertContains(response, "Nouvelle construction")
        self.assertContains(response, "construction-map")

    def test_historique_travaux_list_returns_200(self):
        """La vue du suivi des chantiers et interventions retourne 200 OK."""
        response = self.client.get(f'/{self.dossier.slug}/urbanisme/historique/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'urbanisme/historique/list.html')
        self.assertContains(response, "Bâtiment Pilote")
        self.assertContains(response, "Entreprise BTP Sénégal")

    def test_recommander_emplacements_ajax_endpoint(self):
        """L'algorithme d'aide à la décision classe les zones constructibles en JSON."""
        response = self.client.post(f'/{self.dossier.slug}/urbanisme/recommander/', {
            'type_construction': 'Équipement sportif',
            'superficie_souhaitee': 800.0,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('resultats', data)
        self.assertIn('nb_analyses', data)
        self.assertIn('nb_compatibles', data)

    def test_construction_statut_lifecycle_update(self):
        """La mise à jour de statut d'un projet modifie l'état d'instruction."""
        url = f'/{self.dossier.slug}/urbanisme/{self.projet.pk}/statut/'
        response = self.client.post(url, {'statut': NouvelleConstruction.STATUT_APPROUVE})
        self.assertEqual(response.status_code, 302)

        self.projet.refresh_from_db()
        self.assertEqual(self.projet.statut, NouvelleConstruction.STATUT_APPROUVE)
