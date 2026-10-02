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


class UserUpdateForm(forms.ModelForm):
    """
    Formulaire d'administration pour la mise à jour d'un compte.
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

        # Règle d'or de gouvernance : Unicité absolue du Super Administrateur
        if self.instance and (self.instance.is_superuser or self.instance.role == Role.ROLE_SUPERUSER):
            # Le compte Superuser unique conserve son rang
            self.fields['role'].choices = [(Role.ROLE_SUPERUSER, 'Super Administrateur')]
            self.fields['role'].disabled = True
        else:
            # Aucun autre compte ne peut être élevé au rang de Superuser via l'interface
            if self.operator and (self.operator.is_superuser or self.operator.role == Role.ROLE_SUPERUSER):
                self.fields['role'].choices = [
                    (Role.ROLE_ADMIN, 'Administrateur Territorial'),
                    (Role.ROLE_STANDARD, 'Opérateur Standard'),
                ]
            else:
                self.fields['role'].choices = [
                    (Role.ROLE_STANDARD, 'Opérateur Standard'),
                ]

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
