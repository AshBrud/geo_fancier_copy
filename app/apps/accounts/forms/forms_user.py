from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML
from accounts.models import CustomUser, Role


class StandardUserCreationForm(forms.Form):
    """
    Formulaire institutionnel de création d'un utilisateur / collaborateur.
    Accessible par le Superuser ou un Administrateur territorial habilité.
    Entièrement agnostique et découplé de tout territoire spécifique.
    """
    username = forms.CharField(max_length=150, required=True, label="Identifiant de connexion")
    email = forms.EmailField(required=True, label="Adresse email")
    first_name = forms.CharField(max_length=150, required=True, label="Prénom")
    last_name = forms.CharField(max_length=150, required=True, label="Nom")
    telephone = forms.CharField(max_length=30, required=False, label="Téléphone")
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Mot de passe initial"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Confirmer le mot de passe"
    )

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('username'), Column('email')),
            Row(Column('telephone')),
            Row(Column('password'), Column('confirm_password')),
            HTML('<div class="d-flex justify-content-end gap-2 mt-4">'),
            HTML('<a href="{% url \'accounts:users\' %}" class="btn btn-outline-secondary">Annuler</a>'),
            Submit('submit', 'Créer l\'utilisateur', css_class='btn btn-primary px-4'),
            HTML('</div>'),
        )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Cet identifiant est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà enregistrée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Les deux mots de passe ne correspondent pas.")
        return cleaned_data


class UnifiedUserCreationForm(forms.Form):
    """
    Formulaire unifié de création d'un compte utilisateur en 3 étapes :
    1. Type de compte (standard, admin)
    2. Identité & Coordonnées
    3. Accès et sécurité (mots de passe, rôle territorial, affectation multi-territoires)
    """
    username = forms.CharField(max_length=150, required=True, label="Identifiant de connexion")
    email = forms.EmailField(required=True, label="Adresse email professionnelle")
    first_name = forms.CharField(max_length=150, required=True, label="Prénom")
    last_name = forms.CharField(max_length=150, required=True, label="Nom")
    telephone = forms.CharField(max_length=30, required=False, label="Téléphone professionnel")
    role = forms.ChoiceField(
        choices=[
            (Role.ROLE_STANDARD, 'Opérateur Standard'),
            (Role.ROLE_ADMIN, 'Administrateur Territorial'),
        ],
        initial=Role.ROLE_STANDARD,
        required=True,
        label="Type de compte"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Mot de passe initial"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Confirmer le mot de passe"
    )

    # Rôle local au sein des territoires rattachés
    dossier_role = forms.ChoiceField(
        choices=[
            ('operateur', 'Opérateur SIG / Technicien'),
            ('observateur', 'Observateur / Consultation'),
            ('admin', 'Administrateur du Dossier'),
        ],
        initial='operateur',
        required=False,
        label="Rôle sur les territoires"
    )

    # Mode d'affectation territoriale
    affectation_mode = forms.ChoiceField(
        choices=[
            ('all', 'Tout affecter (Dossiers actuels et futurs)'),
            ('selection', 'Certains dossiers (Sélection ciblée)'),
            ('none', 'Aucun rattachement immédiat'),
        ],
        initial='all',
        required=False,
        label="Périmètre d'affectation"
    )

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)

        # Règle anti-escalade : seul le Superuser peut créer un Administrateur
        if not (self.operator and (self.operator.is_superuser or self.operator.role == Role.ROLE_SUPERUSER)):
            self.fields['role'].choices = [(Role.ROLE_STANDARD, 'Opérateur Standard')]
            self.fields['role'].initial = Role.ROLE_STANDARD

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Cet identifiant est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà enregistrée.")
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == Role.ROLE_ADMIN:
            if not (self.operator and (self.operator.is_superuser or self.operator.role == Role.ROLE_SUPERUSER)):
                raise forms.ValidationError("Seul le Super Administrateur peut désigner un compte Administrateur.")
        if role == Role.ROLE_SUPERUSER:
            raise forms.ValidationError("Le Super Administrateur racine ne peut pas être créé via cette interface.")
        return role

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Les deux mots de passe ne correspondent pas.")

        account_type = cleaned_data.get('role', 'standard')
        dossier_role = cleaned_data.get('dossier_role') or 'operateur'

        # Règle stricte 1 : si type admin -> rôle de dossier forcé à 'admin'
        if account_type == 'admin':
            cleaned_data['dossier_role'] = 'admin'
        elif account_type == 'standard':
            # Règle stricte 2 : un compte standard n'a PAS le droit d'être admin d'un dossier
            if dossier_role == 'admin':
                self.add_error('dossier_role', "Un compte de type Standard ne peut pas être Administrateur de dossier.")
            elif dossier_role not in ['operateur', 'observateur']:
                cleaned_data['dossier_role'] = 'operateur'

        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    """
    Formulaire d'administration pour la mise à jour d'un compte (conservé pour rétro-compatibilité).
    """
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'telephone', 'role', 'photo', 'is_active']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'telephone': 'Téléphone',
            'role': 'Niveau institutionnel',
            'photo': 'Photo de profil',
            'is_active': 'Compte actif (Soft-Delete si décoché)',
        }

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)

        if self.instance and (self.instance.is_superuser or self.instance.role == Role.ROLE_SUPERUSER):
            self.fields['role'].choices = [(Role.ROLE_SUPERUSER, 'Super Administrateur')]
            self.fields['role'].disabled = True
        else:
            if self.operator and (self.operator.is_superuser or self.operator.role == Role.ROLE_SUPERUSER):
                self.fields['role'].choices = [
                    (Role.ROLE_ADMIN, 'Administrateur Territorial'),
                    (Role.ROLE_STANDARD, 'Opérateur Standard'),
                ]
            else:
                self.fields['role'].choices = [
                    (Role.ROLE_STANDARD, 'Opérateur Standard'),
                ]


class UserUpdateModalForm(forms.Form):
    """
    Formulaire modal unifié pour la mise à jour complète d'un utilisateur :
    Identité, type de compte, mot de passe optionnel, statut et affectations territoriales.
    """
    first_name = forms.CharField(max_length=150, required=True, label="Prénom")
    last_name = forms.CharField(max_length=150, required=True, label="Nom")
    email = forms.EmailField(required=True, label="Adresse email professionnelle")
    telephone = forms.CharField(max_length=30, required=False, label="Téléphone professionnel")
    role = forms.ChoiceField(
        choices=[
            (Role.ROLE_STANDARD, 'Opérateur Standard'),
            (Role.ROLE_ADMIN, 'Administrateur Territorial'),
        ],
        required=True,
        label="Type de compte"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Nouveau mot de passe (optionnel)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirmer le nouveau mot de passe"
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Compte actif"
    )
    dossier_role = forms.ChoiceField(
        choices=[
            ('operateur', 'Opérateur SIG / Technicien'),
            ('observateur', 'Observateur / Consultation'),
            ('admin', 'Administrateur du Dossier'),
        ],
        initial='operateur',
        required=False,
        label="Rôle sur les territoires"
    )
    affectation_mode = forms.ChoiceField(
        choices=[
            ('all', 'Tout affecter (Dossiers actuels et futurs)'),
            ('selection', 'Certains dossiers (Sélection ciblée)'),
            ('none', 'Aucun rattachement'),
        ],
        initial='all',
        required=False,
        label="Périmètre d'affectation"
    )

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        self.target_user = kwargs.pop('target_user', None)
        super().__init__(*args, **kwargs)

        if self.target_user:
            self.fields['first_name'].initial = self.target_user.first_name
            self.fields['last_name'].initial = self.target_user.last_name
            self.fields['email'].initial = self.target_user.email
            self.fields['telephone'].initial = self.target_user.telephone
            self.fields['is_active'].initial = self.target_user.is_active

            is_su = self.target_user.is_superuser or self.target_user.role == Role.ROLE_SUPERUSER
            if is_su:
                self.fields['role'].choices = [(Role.ROLE_SUPERUSER, 'Super Administrateur')]
                self.fields['role'].initial = Role.ROLE_SUPERUSER
                self.fields['role'].disabled = True
            elif not (self.operator and (self.operator.is_superuser or self.operator.role == Role.ROLE_SUPERUSER)):
                self.fields['role'].choices = [(Role.ROLE_STANDARD, 'Opérateur Standard')]
                self.fields['role'].initial = Role.ROLE_STANDARD
                self.fields['role'].disabled = True
            else:
                self.fields['role'].initial = self.target_user.role

            aff_initial = 'all' if (self.target_user.acces_tous_territoires or is_su) else 'selection'
            self.fields['affectation_mode'].initial = aff_initial

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = CustomUser.objects.filter(email=email)
        if self.target_user:
            qs = qs.exclude(pk=self.target_user.pk)
        if qs.exists():
            raise forms.ValidationError("Cette adresse email est déjà enregistrée pour un autre compte.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1:
            if len(p1) < 8:
                self.add_error('password', "Le mot de passe doit comporter au moins 8 caractères.")
            if p1 != p2:
                self.add_error('confirm_password', "Les deux mots de passe ne correspondent pas.")

        account_type = cleaned_data.get('role', 'standard')
        dossier_role = cleaned_data.get('dossier_role') or 'operateur'
        if account_type == 'admin':
            cleaned_data['dossier_role'] = 'admin'
        elif account_type == 'standard':
            if dossier_role == 'admin':
                self.add_error('dossier_role', "Un compte de type Standard ne peut pas être Administrateur de dossier.")
            elif dossier_role not in ['operateur', 'observateur']:
                cleaned_data['dossier_role'] = 'operateur'

        return cleaned_data

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('email'), Column('telephone')),
            Row(Column('role'), Column('photo')),
            'is_active',
            HTML('<div class="d-flex justify-content-end gap-2 mt-4">'),
            HTML('<a href="{% url \'accounts:users\' %}" class="btn btn-outline-secondary">Annuler</a>'),
            Submit('submit', 'Enregistrer les modifications', css_class='btn btn-primary px-4'),
            HTML('</div>'),
        )

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == Role.ROLE_SUPERUSER:
            if not (self.instance and (self.instance.is_superuser or self.instance.role == Role.ROLE_SUPERUSER)):
                raise forms.ValidationError("Il ne peut exister qu'un seul compte Super Administrateur sur cette instance.")
        return role


class ProfileForm(forms.ModelForm):
    """
    Formulaire de consultation et d'édition du profil personnel de l'utilisateur connecté.
    """
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'telephone', 'photo']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse email',
            'telephone': 'Téléphone',
            'photo': 'Photo de profil',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('email'), Column('telephone')),
            'photo',
            HTML('<div class="d-flex gap-2 mt-4">'),
            Submit('submit', 'Enregistrer mon profil', css_class='btn btn-primary'),
            HTML('<a href="{% url \'accounts:profile\' %}" class="btn btn-outline-secondary">Annuler</a></div>'),
        )


class RegisterForm(forms.Form):
    """
    Formulaire déprécié conservé uniquement pour éviter toute rupture d'importation héritée.
    L'auto-inscription est désormais strictement fermée.
    """
    pass
