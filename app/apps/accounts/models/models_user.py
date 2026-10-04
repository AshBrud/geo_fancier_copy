from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(UserManager):
    """
    Manager institutionnel pour CustomUser.
    Garantit que la commande native `createsuperuser` initialise automatiquement :
      - role='superuser'
      - is_staff=True
      - is_superuser=True
      - assigned_role lié au profil RBAC superuser
    """
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        from django.core.exceptions import ValidationError
        from django.db.models import Q

        # Règle institutionnelle inviolable : UN SEUL Superuser par instance GéoFoncier
        existing_su = self.model.objects.filter(Q(is_superuser=True) | Q(role='superuser')).first()
        if existing_su and existing_su.username != username:
            raise ValidationError(
                f"Création refusée : L'instance GéoFoncier applique la règle du 'Superuser unique'. "
                f"Le compte maître actuel est déjà '{existing_su.username}' ({existing_su.email or 'aucun email'}). "
                f"Pour changer de superuser, modifiez ou transférez le compte existant."
            )

        extra_fields.setdefault('role', 'superuser')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if 'assigned_role' not in extra_fields:
            try:
                from accounts.models.models_rbac import Role
                su_role = Role.objects.filter(code=Role.ROLE_SUPERUSER).first()
                if su_role:
                    extra_fields['assigned_role'] = su_role
            except Exception:
                pass

        return super().create_superuser(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Modèle utilisateur institutionnel de GéoFoncier V2.
    Gouvernance hiérarchique à 3 niveaux :
      - Superuser (Platform Owner / Root)
      - Admin (Administrateur territorial délégué)
      - Standard (Opérateur métier / Agent terrain / Technicien)
    """
    objects = CustomUserManager()
    # Rôles canoniques V2
    ROLE_SUPERUSER = 'superuser'
    ROLE_ADMIN = 'admin'
    ROLE_STANDARD = 'standard'

    # Rôles historiques V1 (préservés pour intégrité et migration transparente)
    ROLE_DOMAINE = 'domaine_foncier'
    ROLE_ADMINISTRATION = 'administration'
    ROLE_OBSERVATEUR = 'observateur'
    ROLE_MAIRE = 'maire'
    ROLE_CITOYEN = 'citoyen'

    CANONICAL_ROLES_CHOICES = [
        (ROLE_SUPERUSER, 'Super Administrateur'),
        (ROLE_ADMIN, 'Administrateur Territorial'),
        (ROLE_STANDARD, 'Opérateur Standard'),
    ]

    ROLES = [
        # Canoniques V2
        (ROLE_SUPERUSER, 'Super Administrateur'),
        (ROLE_ADMIN, 'Administrateur Territorial'),
        (ROLE_STANDARD, 'Opérateur Standard'),
        # Historiques V1 (préservés pour intégrité et migration transparente)
        (ROLE_DOMAINE, 'Responsable Domaine Foncier (Legacy)'),
        (ROLE_ADMINISTRATION, 'Administration Universitaire (Legacy)'),
        (ROLE_OBSERVATEUR, 'Observateur UAD (Legacy)'),
        (ROLE_MAIRE, 'Responsable communal / Maire (Legacy)'),
        (ROLE_CITOYEN, 'Citoyen (Legacy)'),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLES,
        default=ROLE_STANDARD,
        verbose_name="Rôle statutaire",
        help_text="Niveau hiérarchique principal (Superuser, Admin, Standard)."
    )
    assigned_role = models.ForeignKey(
        'accounts.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_users',
        verbose_name="Profil RBAC associé",
        help_text="Faisceau de permissions atomiques attribué à cet utilisateur."
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name="Créé par",
        help_text="Garantit la traçabilité de la chaîne de mandat."
    )
    telephone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Téléphone"
    )
    village = models.ForeignKey(
        'dossiers.ZoneSecteur',
        related_name='habitants',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Zone ou village de référence",
        help_text="Subdivision spatiale de rattachement (remplacé par les memberships de Dossier)."
    )
    photo = models.ImageField(
        upload_to='profils/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )
    acces_tous_territoires = models.BooleanField(
        default=False,
        verbose_name="Accès universel aux territoires",
        help_text="Accorde l'accès automatique à l'ensemble des dossiers territoriaux (actuels et futurs)."
    )
    user_permissions_custom = models.ManyToManyField(
        'accounts.Permission',
        through='accounts.UserPermissionLink',
        related_name='custom_users',
        blank=True,
        verbose_name="Surcharges individuelles de permissions"
    )
    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Changement de mot de passe obligatoire",
        help_text="Si activé, l'utilisateur doit obligatoirement définir un nouveau mot de passe lors de sa connexion."
    )

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        full_name = self.get_full_name()
        display_name = f"{full_name} ({self.username})" if full_name else self.username
        return f"{display_name} [{self.get_role_display()}]"

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from django.db.models import Q

        # Unicité stricte du compte Super Administrateur racine
        if self.is_superuser or self.role == self.ROLE_SUPERUSER:
            existing = CustomUser.objects.filter(
                Q(is_superuser=True) | Q(role=self.ROLE_SUPERUSER)
            ).exclude(pk=self.pk).first()
            if existing:
                raise ValidationError({
                    'role': (
                        f"Règle de gouvernance violée : Un seul Super Administrateur (Root) est "
                        f"autorisé sur l'instance. Le compte actif est déjà '{existing.username}'."
                    )
                })

    def save(self, *args, **kwargs):
        """
        Garantit la cohérence stricte de la gouvernance :
          - Unicité absolue du compte Superuser : au plus UN superuser dans tout le système.
          - Tout superuser détient automatiquement role='superuser' et is_staff=True.
          - Tout utilisateur avec role='superuser' est promu is_superuser=True et is_staff=True.
          - Attribution automatique du profil RBAC racine ou canonique si manquant.
        """
        from django.core.exceptions import ValidationError
        from django.db.models import Q

        # Contrôle d'intégrité racine : unicité absolue du Super Administrateur
        if self.is_superuser or self.role == self.ROLE_SUPERUSER:
            existing_su = CustomUser.objects.filter(
                Q(is_superuser=True) | Q(role=self.ROLE_SUPERUSER)
            ).exclude(pk=self.pk).first()
            if existing_su:
                raise ValidationError(
                    f"Règle institutionnelle violée : Un unique compte Super Administrateur (Root) "
                    f"est autorisé sur l'instance GéoFoncier. Le compte actif est déjà '{existing_su.username}'."
                )

        update_fields = kwargs.get('update_fields')
        fields_to_add = set()

        if self.is_superuser:
            if self.role != self.ROLE_SUPERUSER:
                self.role = self.ROLE_SUPERUSER
                fields_to_add.add('role')
            if not self.is_staff:
                self.is_staff = True
                fields_to_add.add('is_staff')
        elif self.role == self.ROLE_SUPERUSER:
            if not self.is_superuser:
                self.is_superuser = True
                fields_to_add.add('is_superuser')
            if not self.is_staff:
                self.is_staff = True
                fields_to_add.add('is_staff')

        if not self.assigned_role_id:
            try:
                from accounts.models.models_rbac import Role
                target_code = (
                    Role.ROLE_SUPERUSER if (self.is_superuser or self.role == self.ROLE_SUPERUSER)
                    else Role.ROLE_ADMIN if self.role == self.ROLE_ADMIN
                    else Role.ROLE_STANDARD
                )
                role_obj = Role.objects.filter(code=target_code).first()
                if role_obj:
                    self.assigned_role = role_obj
                    fields_to_add.add('assigned_role')
            except Exception:
                pass

        if update_fields is not None and fields_to_add:
            kwargs['update_fields'] = set(update_fields).union(fields_to_add)

        super().save(*args, **kwargs)

    # --- Évaluation RBAC granulaire (Défense en profondeur) ------------------

    def has_perm_code(self, perm_code: str) -> bool:
        """
        Évalue si l'utilisateur détient la permission atomique [domaine]:[action].
        Logique de résolution :
          1. Inactif -> Faux.
          2. Superuser -> Vrai implicite sur tout le système.
          3. Surcharge directe (UserPermissionLink) prioritaire si définie.
          4. Profil RBAC assigné (assigned_role).
          5. Rôle canonique Admin (détient toutes les perms sauf superuser-exclusives).
          6. Rétrocompatibilité avec les anciens rôles V1.
        """
        if not self.is_active:
            return False

        if self.is_superuser or self.role == self.ROLE_SUPERUSER:
            return True

        # Surcharges individuelles nominatives
        override = self.custom_permission_links.filter(permission__code=perm_code).first()
        if override is not None:
            return override.is_granted

        # Résolution dynamique selon le rôle RBAC assigné ou le rôle statutaire
        from accounts.models import Role
        role_obj = self.assigned_role or Role.objects.filter(code=self.role).first()
        if role_obj and role_obj.permissions.exists():
            return role_obj.permissions.filter(code=perm_code).exists()

        # Rôle canonique Admin territorial (repli si le rôle n'a pas encore de permissions spécifiques en base)
        if self.role == self.ROLE_ADMIN:
            # L'Admin dispose de toutes les permissions sauf les exclusivités Superuser
            superuser_exclusive = {
                'dossier:delegate_role',
                'dossier:supervision',
                'dossier:delete',
            }
            return perm_code not in superuser_exclusive

        # Rétrocompatibilité rôles V1
        if self.role == self.ROLE_DOMAINE:
            domaine_perms = {
                'dossier:view', 'cadastre:view', 'cadastre:create', 'cadastre:update',
                'cadastre:manage_parcelles', 'habitations:view', 'habitations:create',
                'habitations:update', 'audit:view'
            }
            return perm_code in domaine_perms

        if self.role == self.ROLE_MAIRE:
            maire_perms = {
                'dossier:view', 'cadastre:view', 'habitations:view',
                'signalements:view', 'signalements:manage', 'audit:view'
            }
            return perm_code in maire_perms

        if self.role == self.ROLE_CITOYEN:
            citoyen_perms = {
                'dossier:view', 'signalements:view', 'signalements:create'
            }
            return perm_code in citoyen_perms

        if self.role == self.ROLE_OBSERVATEUR:
            return perm_code.endswith(':view') and not (perm_code.startswith('users:') or perm_code.startswith('audit:'))

        return False

    def has_perm_name(self, perm_code: str) -> bool:
        """Alias conventionnel de has_perm_code."""
        return self.has_perm_code(perm_code)

    def get_effective_permissions(self) -> set[str]:
        """Retourne l'ensemble exhaustif des codes de permissions actifs pour l'utilisateur."""
        if not self.is_active:
            return set()

        from accounts.models.models_rbac import Permission

        if self.is_superuser or self.role == self.ROLE_SUPERUSER:
            return set(Permission.objects.values_list('code', flat=True))

        perms = set()
        role_obj = self.assigned_role or Role.objects.filter(code=self.role).first()
        if role_obj:
            perms.update(role_obj.get_permission_codes())

        # Surcharges
        for link in self.custom_permission_links.select_related('permission').all():
            if link.is_granted:
                perms.add(link.permission.code)
            else:
                perms.discard(link.permission.code)

        return perms

    # --- Propriétés de rétrocompatibilité (V1 ➔ V2) ---------------------------

    @property
    def is_admin(self):
        return self.is_superuser or self.role in [self.ROLE_ADMIN, self.ROLE_SUPERUSER]

    @property
    def is_domaine_foncier(self):
        return self.is_admin or self.role == self.ROLE_DOMAINE

    @property
    def can_manage_foncier(self):
        return self.is_admin or self.role in [self.ROLE_DOMAINE, self.ROLE_ADMINISTRATION]

    @property
    def can_view_stats(self):
        return self.is_admin or self.role in [
            self.ROLE_DOMAINE, self.ROLE_ADMINISTRATION, self.ROLE_OBSERVATEUR
        ]

    @property
    def is_role_communal(self):
        return self.role in [self.ROLE_MAIRE, self.ROLE_CITOYEN] and not self.is_superuser

    @property
    def can_view_commune(self):
        return self.is_admin or self.role in [
            self.ROLE_DOMAINE, self.ROLE_ADMINISTRATION, self.ROLE_MAIRE
        ]

    @property
    def can_edit_commune(self):
        return self.is_admin

    @property
    def can_manage_signalements(self):
        return self.is_admin or self.role == self.ROLE_MAIRE


class ActivityLog(models.Model):
    """
    Journal d'audit et de traçabilité des opérations sensibles menées sur la plateforme.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name="Opérateur")
    action = models.CharField(max_length=200, verbose_name="Action effectuée")
    detail = models.TextField(blank=True, verbose_name="Détails contextuels")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Horodatage")

    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal des activités"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp.strftime('%d/%m/%Y %H:%M') if self.timestamp else ''}"
