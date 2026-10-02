"""
SIG Ngogom — cartographie et gestion territoriale de la commune de Ngogom.

Hiérarchie géographique (transposition du modèle « campus » de l'UAD) :

    COMMUNE (limite communale, référence cartographique)
      └─ VILLAGES (polygone)
           └─ MAISONS / parcelles bâties (polygone + statut d'occupation)

Module indépendant : SIGNALEMENTS de problèmes, géolocalisés, avec un
historique de chaque changement de statut et une notification aux
responsables communaux.

Les superficies sont calculées automatiquement en projection métrique
UTM 28N (EPSG:32628), comme dans l'application foncier.
"""
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from django.utils import timezone

UTM_SRID = 32628

# Tolérance de débordement d'un polygone hors de son contenant (limites
# tracées à la main sur fond satellite : quelques mètres d'écart sont normaux).
TOLERANCE_DEBORDEMENT = 0.02  # 2 % de la superficie


def _superficie_m2(geom):
    return round(geom.transform(UTM_SRID, clone=True).area, 2) if geom else None


def _verifier_inclusion(geom, contenant, message):
    """Lève une ValidationError si `geom` déborde de `contenant` au-delà de la tolérance."""
    if not geom or not contenant:
        return
    g = geom.transform(UTM_SRID, clone=True)
    c = contenant.transform(UTM_SRID, clone=True)
    if g.area and g.difference(c).area / g.area > TOLERANCE_DEBORDEMENT:
        raise ValidationError(message)


def _verifier_chevauchement(geom, voisins, libelle):
    """Refuse qu'un polygone en recouvre un autre du même niveau (double comptage)."""
    if not geom:
        return
    g = geom.transform(UTM_SRID, clone=True)
    for autre in voisins.filter(geometrie__intersects=geom):
        commun = g.intersection(autre.geometrie.transform(UTM_SRID, clone=True)).area
        if g.area and commun / g.area > TOLERANCE_DEBORDEMENT:
            raise ValidationError(
                f"Ce polygone chevauche {libelle} « {autre} ». "
                "Les limites ne doivent pas se superposer (double comptage)."
            )


def _code_suivant(model, prefixe, largeur):
    """Identifiant séquentiel lisible : V-001, M-0001…"""
    n = model.objects.filter(code__startswith=prefixe).count() + 1
    while model.objects.filter(code=f"{prefixe}{n:0{largeur}d}").exists():
        n += 1
    return f"{prefixe}{n:0{largeur}d}"


# =============================================================================
#  TERRITOIRE : Commune → Villages → Maisons
# =============================================================================

class Commune(models.Model):
    """Limite administrative de la commune (un seul enregistrement attendu)."""
    nom = models.CharField(max_length=150, default='Ngogom', verbose_name='Nom')
    departement = models.CharField(max_length=100, default='Bambey', verbose_name='Département')
    region = models.CharField(max_length=100, default='Diourbel', verbose_name='Région')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Commune'
        verbose_name_plural = 'Communes'

    def __str__(self):
        return f"Commune de {self.nom}"

    def save(self, *args, **kwargs):
        self.superficie = _superficie_m2(self.geometrie)
        super().save(*args, **kwargs)

    @property
    def superficie_km2(self):
        return round(self.superficie / 1_000_000, 2) if self.superficie else None

    def stats_bati(self):
        """Tableau de bord foncier : chiffres calculés directement depuis la base."""
        maisons = Maison.objects.filter(village__commune=self)
        agg = maisons.aggregate(
            total=Count('id'),
            habitees=Count('id', filter=Q(statut_occupation=Maison.HABITEE)),
            surface=Sum('superficie'),
        )
        return {
            'nb_villages': self.villages.count(),
            'nb_maisons': agg['total'],
            'nb_habitees': agg['habitees'],
            'nb_non_habitees': agg['total'] - agg['habitees'],
            'superficie_batie': round(agg['surface'] or 0, 2),
        }


class Village(models.Model):
    commune = models.ForeignKey(
        Commune, related_name='villages', on_delete=models.CASCADE, verbose_name='Commune',
    )
    code = models.CharField(max_length=30, unique=True, blank=True, verbose_name='Identifiant',
                            help_text='Laissez vide pour une numérotation automatique (V-001, V-002…).')
    nom = models.CharField(max_length=150, verbose_name='Nom du village')
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Village'
        verbose_name_plural = 'Villages'
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def clean(self):
        if not self.geometrie or not self.commune_id:
            return
        _verifier_inclusion(
            self.geometrie, self.commune.geometrie,
            f"Le village doit être situé à l'intérieur des limites de la commune de {self.commune.nom}.",
        )
        _verifier_chevauchement(
            self.geometrie, Village.objects.filter(commune=self.commune).exclude(pk=self.pk), 'le village',
        )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _code_suivant(Village, 'V-', 3)
        self.superficie = _superficie_m2(self.geometrie)
        super().save(*args, **kwargs)

    @property
    def coordonnees_gps(self):
        """Centre du village (lat, lon) — utile pour s'y rendre sur le terrain."""
        if not self.geometrie:
            return None
        c = self.geometrie.point_on_surface
        return round(c.y, 6), round(c.x, 6)

    def stats_bati(self):
        agg = self.maisons.aggregate(
            total=Count('id'),
            habitees=Count('id', filter=Q(statut_occupation=Maison.HABITEE)),
            surface=Sum('superficie'),
        )
        return {
            'nb_maisons': agg['total'],
            'nb_habitees': agg['habitees'],
            'nb_non_habitees': agg['total'] - agg['habitees'],
            'superficie_batie': round(agg['surface'] or 0, 2),
        }


class Maison(models.Model):
    """Maison / parcelle bâtie. Volontairement limitée aux informations utiles
    à la connaissance du bâti : géométrie, superficie, statut d'occupation."""
    HABITEE = 'habitee'
    NON_HABITEE = 'non_habitee'
    STATUTS = [
        (HABITEE, 'Habitée'),
        (NON_HABITEE, 'Non habitée'),
    ]
    COULEURS = {HABITEE: '#DC2626', NON_HABITEE: '#94A3B8'}

    village = models.ForeignKey(
        Village, related_name='maisons', on_delete=models.CASCADE, verbose_name='Village',
    )
    code = models.CharField(max_length=30, unique=True, blank=True, verbose_name='Identifiant',
                            help_text='Laissez vide pour une numérotation automatique (M-0001, M-0002…).')
    statut_occupation = models.CharField(max_length=20, choices=STATUTS, default=HABITEE,
                                         verbose_name="Statut d'occupation")
    geometrie = models.MultiPolygonField(srid=4326, verbose_name='Géométrie')
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie (m²)')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Maison'
        verbose_name_plural = 'Maisons'
        ordering = ['code']

    def __str__(self):
        return self.code or 'Maison'

    def clean(self):
        if not self.geometrie or not self.village_id:
            return
        _verifier_inclusion(
            self.geometrie, self.village.geometrie,
            f"La maison doit être située à l'intérieur du village de {self.village.nom}.",
        )
        _verifier_chevauchement(
            self.geometrie, Maison.objects.filter(village=self.village).exclude(pk=self.pk), 'la maison',
        )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _code_suivant(Maison, 'M-', 4)
        self.superficie = _superficie_m2(self.geometrie)
        super().save(*args, **kwargs)

    @property
    def couleur(self):
        return self.COULEURS.get(self.statut_occupation, '#94A3B8')


class Piste(models.Model):
    """Routes et pistes de la commune (couche de référence)."""
    TYPES = [
        ('route', 'Route bitumée'),
        ('laterite', 'Route en latérite'),
        ('piste', 'Piste'),
    ]
    COULEURS = {'route': '#1F2937', 'laterite': '#B45309', 'piste': '#D97706'}

    nom = models.CharField(max_length=150, blank=True, verbose_name='Nom / tronçon')
    type_voie = models.CharField(max_length=20, choices=TYPES, default='piste', verbose_name='Type')
    geometrie = models.MultiLineStringField(srid=4326, verbose_name='Tracé')
    longueur = models.FloatField(blank=True, null=True, verbose_name='Longueur (m)')

    class Meta:
        verbose_name = 'Route / piste'
        verbose_name_plural = 'Routes et pistes'
        ordering = ['type_voie', 'nom']

    def __str__(self):
        return self.nom or f"{self.get_type_voie_display()} #{self.pk}"

    def save(self, *args, **kwargs):
        if self.geometrie:
            self.longueur = round(self.geometrie.transform(UTM_SRID, clone=True).length, 1)
        super().save(*args, **kwargs)

    @property
    def couleur(self):
        return self.COULEURS.get(self.type_voie, '#D97706')


class OrthophotoCommune(models.Model):
    """Orthophoto drone de la commune (traitée dans WebODM), servie en tuiles
    locales pour rester affichable sans WebODM et depuis un téléphone.
    Distincte des orthophotos du campus (application drones) pour ne pas
    apparaître sur les cartes de l'UAD."""
    nom = models.CharField(max_length=200, verbose_name='Nom')
    source = models.URLField(max_length=500, blank=True, verbose_name='Source (lien WebODM)')
    fichier = models.CharField(max_length=500, blank=True, verbose_name='GeoTIFF (chemin dans MEDIA)')
    tiles_url = models.CharField(max_length=500, verbose_name='URL des tuiles XYZ')
    zoom_min = models.PositiveSmallIntegerField(default=14)
    zoom_max = models.PositiveSmallIntegerField(default=21)
    resolution = models.FloatField(blank=True, null=True, verbose_name='Résolution (cm/pixel)')
    emprise = models.MultiPolygonField(
        srid=4326, verbose_name='Zones couvertes',
        help_text="Contour réel des zones survolées (une partie par zone), calculé depuis l'image.",
    )
    superficie = models.FloatField(blank=True, null=True, verbose_name='Superficie couverte (m²)')
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orthophoto communale'
        verbose_name_plural = 'Orthophotos communales'
        ordering = ['-date_ajout']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        self.superficie = _superficie_m2(self.emprise)
        super().save(*args, **kwargs)

    def zones(self):
        """Une entrée par zone survolée, de la plus grande à la plus petite."""
        parties = sorted(self.emprise, key=lambda p: p.transform(UTM_SRID, clone=True).area, reverse=True)
        return [
            {'numero': i, 'bbox': p.extent, 'superficie_ha': round(p.transform(UTM_SRID, clone=True).area / 10000, 1)}
            for i, p in enumerate(parties, 1)
        ]


# =============================================================================
#  SIGNALEMENTS : problème géolocalisé → suivi → résolution
# =============================================================================

class Signalement(models.Model):
    CATEGORIES = [
        ('eau', 'Eau'),
        ('electricite', 'Électricité'),
        ('route', 'Route / piste'),
        ('assainissement', 'Assainissement'),
        ('eclairage', 'Éclairage public'),
        ('infrastructure', 'Infrastructure'),
        ('autre', 'Autre'),
    ]
    CATEGORIE_STYLE = {
        'eau': ('#0284C7', 'bi-droplet-fill'),
        'electricite': ('#CA8A04', 'bi-lightning-charge-fill'),
        'route': ('#92400E', 'bi-sign-stop-fill'),
        'assainissement': ('#65A30D', 'bi-recycle'),
        'eclairage': ('#EAB308', 'bi-lightbulb-fill'),
        'infrastructure': ('#7C3AED', 'bi-building-exclamation'),
        'autre': ('#6B7280', 'bi-exclamation-lg'),
    }

    NOUVEAU = 'nouveau'
    PRIS_EN_CHARGE = 'pris_en_charge'
    EN_COURS = 'en_cours'
    RESOLU = 'resolu'
    # L'ordre de la liste EST le circuit de traitement.
    STATUTS = [
        (NOUVEAU, 'Nouveau'),
        (PRIS_EN_CHARGE, 'Pris en charge'),
        (EN_COURS, 'En cours'),
        (RESOLU, 'Résolu'),
    ]
    STATUT_COULEURS = {NOUVEAU: '#DC2626', PRIS_EN_CHARGE: '#F59E0B', EN_COURS: '#2563EB', RESOLU: '#16A34A'}

    PRIORITES = [
        ('basse', 'Basse'),
        ('normale', 'Normale'),
        ('haute', 'Haute'),
        ('urgente', 'Urgente'),
    ]

    categorie = models.CharField(max_length=20, choices=CATEGORIES, verbose_name='Catégorie')
    village = models.ForeignKey(
        Village, related_name='signalements', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Village concerné',
        help_text='Détecté automatiquement à partir de la position si vous le laissez vide.',
    )
    titre = models.CharField(max_length=120, verbose_name='Problème en quelques mots',
                             help_text='Ex : Tuyau d\'eau cassé')
    description = models.TextField(verbose_name='Description')
    date_signalement = models.DateTimeField(default=timezone.now, verbose_name='Date du signalement')
    priorite = models.CharField(max_length=10, choices=PRIORITES, default='normale', verbose_name='Priorité')
    statut = models.CharField(max_length=20, choices=STATUTS, default=NOUVEAU, verbose_name='Statut')
    geometrie = models.PointField(srid=4326, verbose_name='Localisation')
    photo = models.ImageField(upload_to='signalements/', blank=True, null=True, verbose_name='Photo (optionnelle)')
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='signalements', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Signalé par',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Signalement'
        verbose_name_plural = 'Signalements'
        ordering = ['-date_signalement']

    def __str__(self):
        return f"{self.numero} — {self.titre}"

    def save(self, *args, **kwargs):
        # Village déduit de la position quand il n'est pas renseigné
        if self.geometrie and not self.village_id:
            self.village = Village.objects.filter(geometrie__contains=self.geometrie).first()
        super().save(*args, **kwargs)

    @property
    def numero(self):
        return f"NG-{self.pk:05d}" if self.pk else 'NG-nouveau'

    @property
    def couleur(self):
        return self.CATEGORIE_STYLE.get(self.categorie, ('#6B7280', ''))[0]

    @property
    def icone(self):
        return self.CATEGORIE_STYLE.get(self.categorie, ('', 'bi-exclamation-lg'))[1]

    @property
    def statut_couleur(self):
        return self.STATUT_COULEURS.get(self.statut, '#6B7280')

    @property
    def est_resolu(self):
        return self.statut == self.RESOLU

    def publier(self):
        """À appeler une fois le signalement enregistré : ouvre son historique et
        notifie tous les responsables communaux (maire + administrateurs).
        L'auteur n'est jamais notifié de son propre signalement. Renvoie le
        nombre de responsables notifiés."""
        from accounts.models import CustomUser
        HistoriqueSignalement.objects.create(
            signalement=self, ancien_statut='', nouveau_statut=self.statut, utilisateur=self.auteur,
            commentaire='Signalement créé',
        )
        responsables = CustomUser.objects.filter(is_active=True).filter(
            Q(role__in=[CustomUser.ROLE_MAIRE, CustomUser.ROLE_ADMIN]) | Q(is_superuser=True)
        ).exclude(pk=self.auteur_id)
        lieu = f" — Village : {self.village.nom}" if self.village else ''
        notifs = Notification.objects.bulk_create([
            Notification(destinataire=u, signalement=self,
                         message=f"Nouveau signalement : {self.get_categorie_display().upper()} — {self.titre}{lieu}")
            for u in responsables
        ])
        return len(notifs)

    def statuts_suivants(self):
        """Statuts atteignables : on avance dans le circuit, jamais en arrière."""
        codes = [c for c, _ in self.STATUTS]
        return [s for s in self.STATUTS if codes.index(s[0]) > codes.index(self.statut)]

    def changer_statut(self, nouveau, utilisateur, commentaire=''):
        """Seul point d'entrée pour faire évoluer un signalement : trace
        l'historique et prévient l'auteur du signalement."""
        if nouveau not in dict(self.statuts_suivants()):
            raise ValidationError("Ce changement de statut n'est pas autorisé.")
        ancien = self.statut
        self.statut = nouveau
        self.save(update_fields=['statut', 'updated_at'])
        HistoriqueSignalement.objects.create(
            signalement=self, ancien_statut=ancien, nouveau_statut=nouveau,
            utilisateur=utilisateur, commentaire=commentaire,
        )
        if self.auteur_id and self.auteur_id != getattr(utilisateur, 'pk', None):
            Notification.objects.create(
                destinataire_id=self.auteur_id, signalement=self,
                message=f"Votre signalement {self.numero} est passé au statut « {self.get_statut_display()} ».",
            )


class HistoriqueSignalement(models.Model):
    signalement = models.ForeignKey(
        Signalement, related_name='historique', on_delete=models.CASCADE, verbose_name='Signalement',
    )
    ancien_statut = models.CharField(max_length=20, choices=Signalement.STATUTS, blank=True,
                                     verbose_name='Ancien statut')
    nouveau_statut = models.CharField(max_length=20, choices=Signalement.STATUTS, verbose_name='Nouveau statut')
    date_changement = models.DateTimeField(auto_now_add=True, verbose_name='Date du changement')
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Par',
    )
    commentaire = models.CharField(max_length=255, blank=True, verbose_name='Commentaire')

    class Meta:
        verbose_name = 'Historique de signalement'
        verbose_name_plural = 'Historique des signalements'
        ordering = ['date_changement']

    def __str__(self):
        return f"{self.signalement.numero} : {self.ancien_statut or '—'} → {self.nouveau_statut}"


class Notification(models.Model):
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='notifications_commune', on_delete=models.CASCADE,
    )
    signalement = models.ForeignKey(Signalement, related_name='notifications', on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    lue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return self.message
