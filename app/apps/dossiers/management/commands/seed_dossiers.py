"""
Commande de Seeding Idempotente : seed_dossiers
Initialise ou synchronise les deux dossiers territoriaux fondateurs de GéoFoncier V2 :
1. Campus UAD Bambey (universite)
2. Commune de Ngogom (commune)
Rattache automatiquement les géométries existantes et crée les adhésions initiales.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from dossiers.models import Dossier, DossierMembership


class Command(BaseCommand):
    help = "Initialise les dossiers territoriaux historiques (UAD Bambey & Commune de Ngogom) de manière idempotente."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("📁 Initialisation des Dossiers Territoriaux V2..."))

        # Récupération optionnelle des entités historiques pour réutiliser leurs polygones
        campus_geom = None
        try:
            from territoire.models import Campus
            campus_obj = Campus.objects.first()
            if campus_obj and campus_obj.geometrie:
                campus_geom = campus_obj.geometrie
                self.stdout.write(self.style.SUCCESS("  ✓ Emprise spatiale du Campus UAD récupérée depuis territoire.Campus"))
        except Exception:
            pass

        commune_geom = None
        try:
            from habitations.models import Commune as CommuneModel
            commune_obj = CommuneModel.objects.first()
            if commune_obj and commune_obj.geometrie:
                commune_geom = commune_obj.geometrie
                self.stdout.write(self.style.SUCCESS("  ✓ Emprise spatiale de Ngogom récupérée depuis habitations.Commune"))
        except Exception:
            pass

        # ---------------------------------------------------------------------
        # 1. DOSSIER 1 : CAMPUS UAD BAMBEY
        # ---------------------------------------------------------------------
        uad_config = {
            "mod_espaces": True,        # Espaces verts, zones pédagogiques, parcelles
            "mod_habitations": True,    # Bâtiments administratifs, amphis, résidences
            "mod_signalements": False,  # Non activé par défaut sur le campus
            "mod_drones": True,         # Missions drones, orthophotos
            "mod_urbanisme": True,      # PDU et extensions du campus
            "mod_toponymie": True,      # Points d'intérêt (amphis, labos)
        }

        dossier_uad, created_uad = Dossier.objects.update_or_create(
            slug="campus-uad-bambey",
            defaults={
                "nom": "Campus UAD Bambey",
                "type_territoire": "universite",
                "description": (
                    "Domaine universitaire de l'Université Alioune Diop de Bambey. "
                    "Gestion du cadastre universitaire, du patrimoine bâti, des voiries "
                    "et des projections d'aménagement du PDU."
                ),
                "srid_metrique": 32628,
                "zoom_defaut": 16,
                "modules_config": uad_config,
                "role_gestionnaire_membres": "admin",
                "is_active": True,
                **({"geometrie": campus_geom} if campus_geom else {}),
            }
        )

        status_uad = "créé avec succès" if created_uad else "mis à jour"
        self.stdout.write(self.style.SUCCESS(f"  [1/2] 🎓 Dossier '{dossier_uad.nom}' ({status_uad})."))

        # ---------------------------------------------------------------------
        # 2. DOSSIER 2 : COMMUNE DE NGOGOM
        # ---------------------------------------------------------------------
        ngogom_config = {
            "mod_espaces": True,        # Pistes, villages, réserves communales
            "mod_habitations": True,    # Maisons, concessions, recensement chefs de famille
            "mod_signalements": True,   # Signalements citoyens d'inondations et dégradations
            "mod_drones": True,         # Orthophotos haute résolution de la commune
            "mod_urbanisme": False,     # Non activé en phase 1
            "mod_toponymie": True,      # Points d'intérêt (écoles, forages, postes de santé)
        }

        dossier_ngogom, created_ngogom = Dossier.objects.update_or_create(
            slug="commune-ngogom",
            defaults={
                "nom": "Commune de Ngogom",
                "type_territoire": "commune",
                "description": (
                    "Collectivité territoriale de Ngogom (Département de Bambey, Région de Diourbel). "
                    "Cartographie des 48 villages, suivi des concessions bâties, pistes rurales "
                    "et gestion des signalements terrain."
                ),
                "srid_metrique": 32628,
                "zoom_defaut": 13,
                "modules_config": ngogom_config,
                "role_gestionnaire_membres": "admin",
                "is_active": True,
                **({"geometrie": commune_geom} if commune_geom else {}),
            }
        )

        status_ngogom = "créé avec succès" if created_ngogom else "mis à jour"
        self.stdout.write(self.style.SUCCESS(f"  [2/2] 🌾 Dossier '{dossier_ngogom.nom}' ({status_ngogom})."))

        # ---------------------------------------------------------------------
        # 3. RATTACHEMENT DES SUPERUSERS EXISTANTS
        # ---------------------------------------------------------------------
        User = get_user_model()
        superusers = User.objects.filter(is_superuser=True)
        for su in superusers:
            for dossier in [dossier_uad, dossier_ngogom]:
                membership, m_created = DossierMembership.objects.get_or_create(
                    user=su,
                    dossier=dossier,
                    defaults={
                        "role": "admin",
                        "assigned_by": su,
                    }
                )
                if m_created:
                    self.stdout.write(f"    ↳ Adhésion Admin créée pour le Superuser '{su.username}' sur '{dossier.nom}'")

        self.stdout.write(self.style.SUCCESS("\n✨ Seeding des Dossiers terminé avec succès !"))
