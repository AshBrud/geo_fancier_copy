from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_DOMAINE = 'domaine_foncier'
    ROLE_ADMINISTRATION = 'administration'
    ROLE_ENSEIGNANT = 'enseignant'
    ROLE_ETUDIANT = 'etudiant'
    ROLE_VISITEUR = 'visiteur'

    ROLES = [
        (ROLE_ADMIN, 'Administrateur'),
        (ROLE_DOMAINE, 'Responsable Domaine Foncier'),
        (ROLE_ADMINISTRATION, 'Administration Universitaire'),
        (ROLE_ENSEIGNANT, 'Enseignant'),
        (ROLE_ETUDIANT, 'Etudiant'),
        (ROLE_VISITEUR, 'Visiteur'),
    ]

    role = models.CharField(max_length=20, choices=ROLES, default=ROLE_VISITEUR)
    telephone = models.CharField(max_length=20, blank=True)
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
        return self.role in [self.ROLE_ADMIN, self.ROLE_DOMAINE, self.ROLE_ADMINISTRATION,
                             self.ROLE_ENSEIGNANT, self.ROLE_ETUDIANT]


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
