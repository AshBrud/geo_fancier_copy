import uuid
from typing import Dict, Any, List

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.text import slugify

from .models_base import TimeStampedModel


def get_default_modules_config() -> Dict[str, bool]:
    """Retourne la configuration par défaut des modules pour un nouveau dossier."""
    return {
        "mod_espaces": True,        # Cadastre, parcelles, voiries
        "mod_habitations": True,    # Bâti, concessions, recensement
        "mod_signalements": True,   # Signalements d'anomalies de terrain
        "mod_drones": True,         # Imagerie aérienne, orthophotos
        "mod_urbanisme": False,     # PDU, projections d'aménagement
        "mod_toponymie": True,      # Points d'intérêt et repères
    }


class Dossier(TimeStampedModel):
    """
    Espace de travail territorial autonome et étanche (Workspace).
    Chaque dossier représente un périmètre d'autorité foncière ou domaniale
    (commune, campus universitaire, zone cadastrale, direction ministérielle).
    """
    TYPE_TERRITOIRE_CHOICES = [
        ('commune', 'Collectivité Territoriale / Commune'),
        ('universite', 'Domaine Universitaire / Campus'),
        ('cadastre', 'Direction du Cadastre / Circonscription'),
        ('ministere', 'Périmètre Ministériel / Étatique'),
        ('autre', 'Autre Périmètre Territorial'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Identifiant UUID"
    )
    nom = models.CharField(
        max_length=255,
        verbose_name="Nom du dossier / territoire",
        help_text="Ex: Commune de Ngogom ou Campus UAD Bambey"
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Identifiant URL (Slug)",
        help_text="Généré automatiquement ou personnalisé pour les URLs contextuelles."
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description & Contexte administratif",
        help_text="Précisions sur la mission territoriale, décrets ou mandats."
    )
    type_territoire = models.CharField(
        max_length=50,
        choices=TYPE_TERRITOIRE_CHOICES,
        default='commune',
        verbose_name="Type d'entité territoriale"
    )

    # Délimitation et géométrie spatiale
    geometrie = gis_models.MultiPolygonField(
        srid=4326,
        null=True,
        blank=True,
        verbose_name="Emprise spatiale (EPSG:4326)",
        help_text="Polygone ou MultiPolygone englobant le territoire."
    )
    srid_metrique = models.IntegerField(
        default=32628,
        verbose_name="SRID Métrique UTM",
        help_text="Projection métrique de référence (ex: 32628 pour UTM 28N Sénégal)."
    )
    centre_carte = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        verbose_name="Point central de cadrage",
        help_text="Coordonnées initiales pour le centrage de la carte Leaflet."
    )
    zoom_defaut = models.PositiveSmallIntegerField(
        default=14,
        verbose_name="Niveau de zoom initial Leaflet"
    )
    superficie_ha = models.FloatField(
        default=0.0,
        verbose_name="Superficie calculée (Hectares)",
        help_text="Calculée automatiquement via transformation métrique UTM."
    )

    # Modularité & Habilitations
    modules_config = models.JSONField(
        default=get_default_modules_config,
        blank=True,
        verbose_name="Configuration des modules métier activés"
    )
    role_gestionnaire_membres = models.CharField(
        max_length=50,
        default='admin',
        verbose_name="Rôle gestionnaire délégué",
        help_text="Rôle habilité par le Superuser pour assigner des membres à ce dossier (défaut: 'admin')."
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Dossier actif",
        help_text="Désactiver pour archiver un dossier sans supprimer ses données historiques."
    )

    class Meta:
        verbose_name = "Dossier Territorial"
        verbose_name_plural = "Dossiers Territoriaux"
        ordering = ['nom']

    def __str__(self) -> str:
        return f"{self.nom} ({self.get_type_territoire_display()})"

    def clean(self):
        super().clean()
        if not self.slug and self.nom:
            self.slug = slugify(self.nom)

    def save(self, *args, **kwargs):
        # 1. Génération automatique du slug si non renseigné
        if not self.slug and self.nom:
            self.slug = slugify(self.nom)

        # 2. Traitement géomatique automatique
        if self.geometrie:
            # Centrage automatique si non spécifié manuellement
            if not self.centre_carte:
                self.centre_carte = self.geometrie.centroid

            # Calcul précis de la superficie métrique en hectares
            try:
                geom_metrique = self.geometrie.transform(self.srid_metrique, clone=True)
                self.superficie_ha = round(geom_metrique.area / 10000.0, 2)
            except Exception:
                # Si la transformation métrique échoue (librairie absente en dev local), conserver l'existant
                pass

        super().save(*args, **kwargs)

    # Helpers de gestion modulaire
    def is_module_enabled(self, module_key: str) -> bool:
        """Vérifie si un module métier spécifique est activé pour ce dossier."""
        if not isinstance(self.modules_config, dict):
            return False
        return bool(self.modules_config.get(module_key, False))

    def enable_module(self, module_key: str) -> None:
        """Active un module métier pour ce dossier."""
        if not isinstance(self.modules_config, dict):
            self.modules_config = get_default_modules_config()
        self.modules_config[module_key] = True

    def disable_module(self, module_key: str) -> None:
        """Désactive un module métier pour ce dossier."""
        if not isinstance(self.modules_config, dict):
            self.modules_config = get_default_modules_config()
        self.modules_config[module_key] = False

    def get_active_modules(self) -> List[str]:
        """Retourne la liste des clés de modules actifs."""
        if not isinstance(self.modules_config, dict):
            return []
        return [k for k, v in self.modules_config.items() if v]

    def can_user_manage_members(self, user) -> bool:
        """
        Détermine si un utilisateur est habilité à assigner/gérer les membres de ce dossier.
        - Superuser : toujours autorisé (souveraineté absolue).
        - Utilisateur Admin : autorisé si le dossier délègue au rôle 'admin' et qu'il est membre admin.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        # Vérifier l'adhésion au dossier
        membership = self.memberships.filter(user=user).first()
        if not membership:
            return False

        # Si le rôle délégué correspond au rôle de l'adhésion
        if membership.role == self.role_gestionnaire_membres:
            return True

        return False


class DossierMembership(TimeStampedModel):
    """
    Table de liaison institutionnelle scopée entre un Utilisateur et un Dossier.
    Définit le rôle local et la traçabilité de l'adhésion (qui a assigné le membre et quand).
    """
    ROLE_CHOICES = [
        ('admin', 'Administrateur du Dossier'),
        ('operateur', 'Opérateur SIG / Technicien'),
        ('observateur', 'Observateur / Consultation'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Identifiant UUID"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dossier_memberships',
        verbose_name="Utilisateur affecté"
    )
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name="Dossier de rattachement"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_dossier_memberships',
        verbose_name="Affecté par",
        help_text="Consigne le Superuser ou l'Admin délégué ayant accordé l'accès."
    )
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='observateur',
        verbose_name="Rôle dans l'espace de travail"
    )
    permissions_override = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Surcharges de permissions locales",
        help_text="Ajustements spécifiques de droits attribués à cet utilisateur sur ce dossier."
    )

    class Meta:
        verbose_name = "Affectation à un Dossier"
        verbose_name_plural = "Affectations aux Dossiers"
        unique_together = ('user', 'dossier')
        ordering = ['-date_creation']

    def __str__(self) -> str:
        return f"{self.user} -> {self.dossier.nom} ({self.get_role_display()})"

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    @property
    def is_operateur(self) -> bool:
        return self.role == 'operateur'

    @property
    def is_observateur(self) -> bool:
        return self.role == 'observateur'

    def has_permission(self, permission_code: str) -> bool:
        """
        Vérifie si le membre dispose d'une permission spécifique sur ce dossier.
        Prend en compte :
        1. Le rôle local (ex: admin a accès étendu).
        2. Les surcharges explicites (permissions_override).
        """
        if self.is_admin:
            return True

        # Vérification des surcharges explicites : {"cadastre:manage_parcelles": true}
        if isinstance(self.permissions_override, dict):
            if permission_code in self.permissions_override:
                return bool(self.permissions_override[permission_code])

        # Habilitations par défaut selon le rôle
        if self.is_operateur:
            # Un opérateur a les droits de lecture et de saisie opérationnelle
            return not (permission_code.endswith(':delete') or 'dossier:' in permission_code)

        if self.is_observateur:
            # Un observateur n'a que des droits de lecture
            return permission_code.endswith(':view')

        return False
