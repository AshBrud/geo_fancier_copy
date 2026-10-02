from django.db import models
from dossiers.models.models_base import TimeStampedModel


class Permission(TimeStampedModel):
    """
    Permission atomique standardisée selon la nomenclature [domaine]:[action]
    ou [domaine]:[sous-domaine]:[action].
    Exemples : 'cadastre:view', 'users:create', 'dossier:configure_modules'.
    """
    DOMAINE_DOSSIER = 'dossier'
    DOMAINE_USERS = 'users'
    DOMAINE_AUDIT = 'audit'
    DOMAINE_CADASTRE = 'cadastre'
    DOMAINE_HABITATIONS = 'habitations'
    DOMAINE_SIGNALEMENTS = 'signalements'
    DOMAINE_DRONES = 'drones'
    DOMAINE_URBANISME = 'urbanisme'
    DOMAINE_TOPONYMIE = 'toponymie'
    DOMAINE_SETTINGS = 'settings'

    DOMAINES = [
        (DOMAINE_DOSSIER, 'Périmètres & Dossiers'),
        (DOMAINE_USERS, 'Comptes & Gouvernance'),
        (DOMAINE_AUDIT, 'Audit & Sécurité'),
        (DOMAINE_CADASTRE, 'Cadastre & Espaces'),
        (DOMAINE_HABITATIONS, 'Habitations & Bâti'),
        (DOMAINE_SIGNALEMENTS, 'Signalements & Dommages'),
        (DOMAINE_DRONES, 'Drones & Imagerie'),
        (DOMAINE_URBANISME, 'Urbanisme & PDU'),
        (DOMAINE_TOPONYMIE, 'Toponymie & POI'),
        (DOMAINE_SETTINGS, 'Configuration Système'),
    ]

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Code d'habilitation",
        help_text="Nomenclature standardisée [domaine]:[action] (ex: 'cadastre:view')."
    )
    nom = models.CharField(
        max_length=150,
        verbose_name="Libellé fonctionnel",
        help_text="Intitulé compréhensible pour l'interface de gestion."
    )
    domaine = models.CharField(
        max_length=50,
        choices=DOMAINES,
        db_index=True,
        verbose_name="Domaine métier",
        help_text="Module fonctionnel auquel est rattachée la permission."
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description & Portée",
        help_text="Explication détaillée de la portée et des prérogatives conférées."
    )

    class Meta:
        verbose_name = "Permission RBAC"
        verbose_name_plural = "Permissions RBAC"
        ordering = ['domaine', 'code']

    def __str__(self):
        return f"{self.code} ({self.nom})"


class Role(TimeStampedModel):
    """
    Rôle institutionnel regroupant un ensemble cohérent de permissions.
    Prend en charge les 3 rôles canoniques ('superuser', 'admin', 'standard')
    ainsi que des rôles spécialisés métier configurables.
    """
    ROLE_SUPERUSER = 'superuser'
    ROLE_ADMIN = 'admin'
    ROLE_STANDARD = 'standard'

    CANONICAL_ROLES = (ROLE_SUPERUSER, ROLE_ADMIN, ROLE_STANDARD)

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Identifiant unique du rôle",
        help_text="Code technique immuable (ex: 'admin', 'standard', 'technicien_sig')."
    )
    nom = models.CharField(
        max_length=100,
        verbose_name="Nom du rôle",
        help_text="Libellé affiché dans les interfaces (ex: 'Administrateur Territorial')."
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description du rôle"
    )
    is_canonical = models.BooleanField(
        default=False,
        verbose_name="Rôle canonique système",
        help_text="Indique si ce rôle fait partie de la gouvernance socle (Superuser, Admin, Standard)."
    )
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermissionLink',
        related_name='roles',
        blank=True,
        verbose_name="Permissions associées"
    )

    class Meta:
        verbose_name = "Rôle RBAC"
        verbose_name_plural = "Rôles RBAC"
        ordering = ['code']

    def __str__(self):
        return f"{self.nom} [{self.code}]"

    def get_permission_codes(self) -> set[str]:
        """Retourne l'ensemble des codes de permissions associés à ce rôle."""
        return set(self.permissions.values_list('code', flat=True))


class RolePermissionLink(TimeStampedModel):
    """
    Table de liaison M2M entre un Rôle et une Permission avec traçabilité d'audit.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='permission_links',
        verbose_name="Rôle"
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_links',
        verbose_name="Permission"
    )

    class Meta:
        verbose_name = "Liaison Rôle - Permission"
        verbose_name_plural = "Liaisons Rôles - Permissions"
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.code} ➔ {self.permission.code}"


class UserPermissionLink(TimeStampedModel):
    """
    Table de dérogation / surcharge directe de permissions pour un utilisateur spécifique.
    Permet à un Admin d'accorder (is_granted=True) ou de révoquer (is_granted=False)
    une permission atomique nominativement, dans la limite de son enveloppe de délégation.
    """
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='custom_permission_links',
        verbose_name="Utilisateur"
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_links',
        verbose_name="Permission"
    )
    is_granted = models.BooleanField(
        default=True,
        verbose_name="Accordé",
        help_text="True si la permission est explicitement accordée, False si explicitement révoquée."
    )

    class Meta:
        verbose_name = "Dérogation Permission Utilisateur"
        verbose_name_plural = "Dérogations Permissions Utilisateurs"
        unique_together = ('user', 'permission')

    def __str__(self):
        status = "ACCORDÉ" if self.is_granted else "RÉVOQUÉ"
        return f"{self.user.username} : {self.permission.code} [{status}]"
