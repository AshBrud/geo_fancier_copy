from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import CustomUser, Permission, Role, RolePermissionLink


class Command(BaseCommand):
    help = "Initialisation DML idempotente du catalogue de permissions RBAC et des rôles canoniques."

    PERMISSIONS_CATALOG = [
        # --- Périmètres & Dossiers ---
        {
            'code': 'dossier:view',
            'nom': 'Consulter les dossiers',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Accès à la galerie et aux données des dossiers territoriaux autorisés.',
        },
        {
            'code': 'dossier:create',
            'nom': 'Créer un dossier territorial',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Création d\'un nouveau périmètre et paramétrage SIG initial.',
        },
        {
            'code': 'dossier:update',
            'nom': 'Mettre à jour un dossier',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Modification de l\'emprise spatiale, des métadonnées ou coordonnées du dossier.',
        },
        {
            'code': 'dossier:delete',
            'nom': 'Supprimer / Archiver un dossier',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Suppression logique ou archivage définitif d\'un espace de travail.',
        },
        {
            'code': 'dossier:configure_modules',
            'nom': 'Configurer les modules activés',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Activation ou désactivation modulaire (mod_espaces, mod_habitations, etc.).',
        },
        {
            'code': 'dossier:assign_members',
            'nom': 'Assigner des membres au dossier',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Affecter un compte Standard ou un collaborateur au dossier territorial.',
        },
        {
            'code': 'dossier:revoke_members',
            'nom': 'Révoquer des membres du dossier',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Retirer l\'accès d\'un utilisateur au dossier.',
        },
        {
            'code': 'dossier:delegate_role',
            'nom': 'Déléguer le rôle assigneur',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Désigner quel rôle administrateur peut affecter des membres (Superuser exclusivement).',
        },
        {
            'code': 'dossier:supervision',
            'nom': 'Supervision globale transverse',
            'domaine': Permission.DOMAINE_DOSSIER,
            'description': 'Accès à la vue macroscopique de l\'ensemble du parc national (Superuser exclusivement).',
        },

        # --- Comptes & Gouvernance ---
        {
            'code': 'users:view',
            'nom': 'Consulter les utilisateurs',
            'domaine': Permission.DOMAINE_USERS,
            'description': 'Lister les comptes du périmètre d\'autorité institutionnelle.',
        },
        {
            'code': 'users:create',
            'nom': 'Créer un compte utilisateur',
            'domaine': Permission.DOMAINE_USERS,
            'description': 'Créer un compte sous son niveau d\'autorité hiérarchique.',
        },
        {
            'code': 'users:update',
            'nom': 'Modifier un utilisateur',
            'domaine': Permission.DOMAINE_USERS,
            'description': 'Mettre à jour le profil, coordonnées ou mot de passe d\'un collaborateur.',
        },
        {
            'code': 'users:deactivate',
            'nom': 'Désactiver un compte (Soft-Delete)',
            'domaine': Permission.DOMAINE_USERS,
            'description': 'Désactiver logiquement un compte sans rupture de traçabilité.',
        },
        {
            'code': 'users:reset_password',
            'nom': 'Réinitialiser le mot de passe',
            'domaine': Permission.DOMAINE_USERS,
            'description': 'Déclencher la réinitialisation de mot de passe d\'un agent.',
        },

        # --- Audit & Sécurité ---
        {
            'code': 'audit:view',
            'nom': 'Consulter le journal d\'activité',
            'domaine': Permission.DOMAINE_AUDIT,
            'description': 'Consulter les journaux d\'audit et d\'activité du périmètre.',
        },
        {
            'code': 'audit:export',
            'nom': 'Exporter les journaux d\'audit',
            'domaine': Permission.DOMAINE_AUDIT,
            'description': 'Export certifié des journaux d\'audit pour contrôle légal.',
        },

        # --- Cadastre & Espaces ---
        {
            'code': 'cadastre:view',
            'nom': 'Consulter le cadastre',
            'domaine': Permission.DOMAINE_CADASTRE,
            'description': 'Visualisation des sous-espaces, parcelles et linéaires viaires.',
        },
        {
            'code': 'cadastre:edit_bounds',
            'nom': 'Délimiter le périmètre global',
            'domaine': Permission.DOMAINE_CADASTRE,
            'description': 'Retoucher le polygone englobant de la collectivité ou du campus.',
        },
        {
            'code': 'cadastre:manage_zones',
            'nom': 'Gérer les sous-espaces et villages',
            'domaine': Permission.DOMAINE_CADASTRE,
            'description': 'Créer, modifier, découper des villages ou secteurs d\'aménagement.',
        },
        {
            'code': 'cadastre:manage_parcelles',
            'nom': 'Gérer les parcelles et terrains',
            'domaine': Permission.DOMAINE_CADASTRE,
            'description': 'Créer, borner et affecter les parcelles cadastrales.',
        },
        {
            'code': 'cadastre:manage_voiries',
            'nom': 'Gérer les voiries et pistes',
            'domaine': Permission.DOMAINE_CADASTRE,
            'description': 'Tracer, classifier et maintenir le réseau viaire.',
        },
        {
            'code': 'cadastre:manage_espaces_verts',
            'nom': 'Gérer les réserves foncières',
            'domaine': Permission.DOMAINE_CADASTRE,
            'description': 'Recensement et protection des zones non constructibles ou réserves.',
        },

        # --- Habitations & Bâti ---
        {
            'code': 'habitations:view',
            'nom': 'Consulter l\'inventaire du bâti',
            'domaine': Permission.DOMAINE_HABITATIONS,
            'description': 'Accès aux fiches des bâtiments, concessions et habitants.',
        },
        {
            'code': 'habitations:create',
            'nom': 'Recenser un nouveau bâti',
            'domaine': Permission.DOMAINE_HABITATIONS,
            'description': 'Numérisation au sol d\'un nouveau bâtiment ou d\'une concession.',
        },
        {
            'code': 'habitations:update',
            'nom': 'Modifier les attributs du bâti',
            'domaine': Permission.DOMAINE_HABITATIONS,
            'description': 'Mise à jour des données d\'occupation, étages, usage.',
        },
        {
            'code': 'habitations:delete',
            'nom': 'Supprimer une unité bâtie',
            'domaine': Permission.DOMAINE_HABITATIONS,
            'description': 'Suppression ou radiation d\'un édifice recensé.',
        },
        {
            'code': 'habitations:import_sig',
            'nom': 'Importer des couches SIG bâti',
            'domaine': Permission.DOMAINE_HABITATIONS,
            'description': 'Import massif de bâtiments (GeoJSON, Shapefile, DXF).',
        },
        {
            'code': 'habitations:manage_chantiers',
            'nom': 'Suivi des travaux et chantiers',
            'domaine': Permission.DOMAINE_HABITATIONS,
            'description': 'Contrôle des chantiers en cours et autorisations d\'aménager.',
        },

        # --- Signalements & Dommages ---
        {
            'code': 'signalements:view',
            'nom': 'Consulter les signalements',
            'domaine': Permission.DOMAINE_SIGNALEMENTS,
            'description': 'Liste et carte des incidents fonciers, voiries ou domaniaux.',
        },
        {
            'code': 'signalements:create',
            'nom': 'Signaler une anomalie',
            'domaine': Permission.DOMAINE_SIGNALEMENTS,
            'description': 'Création géolocalisée d\'un incident terrain avec photo.',
        },
        {
            'code': 'signalements:manage',
            'nom': 'Traiter les signalements',
            'domaine': Permission.DOMAINE_SIGNALEMENTS,
            'description': 'Prise en charge, affectation et clôture des signalements.',
        },
        {
            'code': 'signalements:delete',
            'nom': 'Supprimer un signalement',
            'domaine': Permission.DOMAINE_SIGNALEMENTS,
            'description': 'Archivage ou rejet motivé d\'un signalement.',
        },

        # --- Drones & Imagerie ---
        {
            'code': 'drones:view',
            'nom': 'Consulter l\'imagerie drone',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Galerie des vols, orthophotos et flux de télédétection.',
        },
        {
            'code': 'drones:manage_missions',
            'nom': 'Gérer les missions de vol',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Planification des plans de vol et métadonnées d\'acquisition.',
        },
        {
            'code': 'drones:upload_photos',
            'nom': 'Téléverser des clichés bruts',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Téléversement de photos aériennes géoréférencées.',
        },
        {
            'code': 'drones:import_orthophoto',
            'nom': 'Importer des rasters GeoTIFF',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Téléversement et ingestion de rasters haute résolution.',
        },
        {
            'code': 'drones:integrate_orthophoto',
            'nom': 'Intégrer au SIG (Tuiles XYZ)',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Génération du dallage XYZ et activation de la couche cartographique.',
        },
        {
            'code': 'drones:delete_orthophoto',
            'nom': 'Supprimer une orthophoto',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Suppression définitive d\'un raster ou d\'une mission de vol.',
        },
        {
            'code': 'drones:live_stream',
            'nom': 'Flux vidéo direct & captures',
            'domaine': Permission.DOMAINE_DRONES,
            'description': 'Surveillance temps réel et capture de flux vidéo en direct.',
        },

        # --- Urbanisme & PDU ---
        {
            'code': 'urbanisme:view',
            'nom': 'Consulter le PDU et le zonage',
            'domaine': Permission.DOMAINE_URBANISME,
            'description': 'Visualisation du plan d\'urbanisme, des zones réservées et coefficients.',
        },
        {
            'code': 'urbanisme:simulate',
            'nom': 'Lancer une simulation / recommandation',
            'domaine': Permission.DOMAINE_URBANISME,
            'description': 'Moteur d\'aide à la décision d\'implantation spatiale optimale.',
        },
        {
            'code': 'urbanisme:create_projet',
            'nom': 'Créer un projet d\'aménagement',
            'domaine': Permission.DOMAINE_URBANISME,
            'description': 'Enregistrement d\'un projet d\'édifice ou d\'infrastructure.',
        },
        {
            'code': 'urbanisme:manage_projet',
            'nom': 'Piloter les phases de projet',
            'domaine': Permission.DOMAINE_URBANISME,
            'description': 'Suivi des validations et ajustements techniques de projet.',
        },

        # --- Toponymie & POI ---
        {
            'code': 'toponymie:view',
            'nom': 'Consulter les repères et POI',
            'domaine': Permission.DOMAINE_TOPONYMIE,
            'description': 'Affichage des points remarquables et équipements publics.',
        },
        {
            'code': 'toponymie:manage',
            'nom': 'Gérer les points d\'intérêt',
            'domaine': Permission.DOMAINE_TOPONYMIE,
            'description': 'Création, modification et labellisation de points d\'intérêt.',
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🌱 [seed_rbac] Démarrage du seeding idempotent des permissions et rôles..."))

        created_perms = 0
        updated_perms = 0

        with transaction.atomic():
            # 1. Seeding des permissions
            perm_objects = {}
            for item in self.PERMISSIONS_CATALOG:
                perm, created = Permission.objects.update_or_create(
                    code=item['code'],
                    defaults={
                        'nom': item['nom'],
                        'domaine': item['domaine'],
                        'description': item['description'],
                    }
                )
                perm_objects[perm.code] = perm
                if created:
                    created_perms += 1
                else:
                    updated_perms += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ Permissions traitées : {len(perm_objects)} au total "
                    f"({created_perms} créées, {updated_perms} synchronisées)."
                )
            )

            # 2. Configuration des 3 Rôles Canoniques V2
            roles_config = [
                {
                    'code': Role.ROLE_SUPERUSER,
                    'nom': 'Super Administrateur',
                    'description': 'Maître absolu de la plateforme. Détient l\'intégralité des prérogatives système.',
                    'is_canonical': True,
                    'permissions': list(perm_objects.values()),
                },
                {
                    'code': Role.ROLE_ADMIN,
                    'nom': 'Administrateur Territorial',
                    'description': 'Délégué institutionnel sur un territoire. Gère les membres, paramétrages et données métier.',
                    'is_canonical': True,
                    # Toutes les permissions SAUF les exclusivités souveraines du Superuser
                    'permissions': [
                        p for code, p in perm_objects.items()
                        if code not in {'dossier:delegate_role', 'dossier:supervision', 'dossier:delete'}
                    ],
                },
                {
                    'code': Role.ROLE_STANDARD,
                    'nom': 'Opérateur Standard',
                    'description': 'Opérateur opérationnel de terrain ou instructeur. Accès strictement limité aux modules autorisés.',
                    'is_canonical': True,
                    # Habilitations de base en consultation
                    'permissions': [
                        p for code, p in perm_objects.items()
                        if code in {
                            'dossier:view',
                            'cadastre:view',
                            'habitations:view',
                            'signalements:view',
                            'signalements:create',
                            'drones:view',
                            'urbanisme:view',
                            'toponymie:view',
                        }
                    ],
                },
            ]

            for r_data in roles_config:
                role, created = Role.objects.update_or_create(
                    code=r_data['code'],
                    defaults={
                        'nom': r_data['nom'],
                        'description': r_data['description'],
                        'is_canonical': r_data['is_canonical'],
                    }
                )
                role.permissions.set(r_data['permissions'])
                action_str = "créé" if created else "actualisé"
                self.stdout.write(f"  👑 Rôle '{role.code}' {action_str} avec {role.permissions.count()} permissions.")

            # 3. Synchronisation automatique des utilisateurs existants
            User = get_user_model()
            superuser_role = Role.objects.get(code=Role.ROLE_SUPERUSER)
            admin_role = Role.objects.get(code=Role.ROLE_ADMIN)
            standard_role = Role.objects.get(code=Role.ROLE_STANDARD)

            synced_users = 0
            for user in User.objects.all():
                modified = False
                if user.is_superuser:
                    if user.role != Role.ROLE_SUPERUSER or user.assigned_role != superuser_role:
                        user.role = Role.ROLE_SUPERUSER
                        user.assigned_role = superuser_role
                        modified = True
                elif user.role in [CustomUser.ROLE_ADMIN, 'admin']:
                    if user.assigned_role != admin_role:
                        user.role = Role.ROLE_ADMIN
                        user.assigned_role = admin_role
                        modified = True
                else:
                    if not user.assigned_role:
                        user.assigned_role = standard_role
                        modified = True

                if modified:
                    user.save(update_fields=['role', 'assigned_role'])
                    synced_users += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  👥 Synchronisation des profils utilisateurs : {synced_users} compte(s) rattaché(s) à leur rôle RBAC."
                )
            )

        self.stdout.write(self.style.SUCCESS("✨ [seed_rbac] Seeding RBAC terminé avec succès et de manière 100% idempotente."))
