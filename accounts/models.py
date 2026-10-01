from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_DOMAINE = 'domaine_foncier'
    ROLE_ADMINISTRATION = 'administration'
    ROLE_OBSERVATEUR = 'observateur'
    # Rôles propres au module communal (Ngogom)
    ROLE_MAIRE = 'maire'
    ROLE_CITOYEN = 'citoyen'

    ROLES = [
        (ROLE_ADMIN, 'Administrateur'),
        (ROLE_DOMAINE, 'Responsable Domaine Foncier'),
        (ROLE_ADMINISTRATION, 'Administration Universitaire'),
        (ROLE_OBSERVATEUR, 'Observateur UAD'),
        (ROLE_MAIRE, 'Responsable communal / Maire'),
        (ROLE_CITOYEN, 'Citoyen'),
    ]

    role = models.CharField(max_length=20, choices=ROLES, default=ROLE_OBSERVATEUR)
    telephone = models.CharField(max_length=20, blank=True)
    # Village de résidence (habitants de Ngogom) : permet à l'équipe technique
    # de savoir où intervenir et qui appeler.
    village = models.ForeignKey(
        'commune.Village', related_name='habitants', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Village',
    )
    photo = models.ImageField(upload_to='profils/', blank=True, null=True)

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def is_domaine_foncier(self):
        return self.role in [self.ROLE_ADMIN, self.ROLE_DOMAINE]

    @property
    def can_manage_foncier(self):
        return self.role in [self.ROLE_ADMIN, self.ROLE_DOMAINE, self.ROLE_ADMINISTRATION]

    @property
    def can_view_stats(self):
        return self.role in [self.ROLE_ADMIN, self.ROLE_DOMAINE,
                             self.ROLE_ADMINISTRATION, self.ROLE_OBSERVATEUR]

    # --- Module communal ------------------------------------------------------

    @property
    def is_role_communal(self):
        """Maire et citoyens n'utilisent que le module communal (pas le campus UAD)."""
        return self.role in [self.ROLE_MAIRE, self.ROLE_CITOYEN] and not self.is_superuser

    @property
    def can_view_commune(self):
        """Consulter villages, maisons et superficies."""
        return self.is_admin or self.role in [self.ROLE_DOMAINE, self.ROLE_ADMINISTRATION, self.ROLE_MAIRE]

    @property
    def can_edit_commune(self):
        """Gérer la limite communale, les villages, les maisons et les pistes."""
        return self.is_admin

    @property
    def can_manage_signalements(self):
        """Voir tous les signalements, recevoir les notifications, changer les statuts."""
        return self.is_admin or self.role == self.ROLE_MAIRE


class ActivityLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Journal d\'activité'
        verbose_name_plural = 'Journal des activités'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
