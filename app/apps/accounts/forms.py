import re

from django import forms
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, HTML
from .models import CustomUser


def normaliser_telephone(valeur):
    """Numéro sénégalais sur 9 chiffres (77 123 45 67, +221 77…, 00221 77…) → « 771234567 ».
    Renvoie None si la valeur n'est pas un numéro valide."""
    chiffres = re.sub(r'[\s.\-()]', '', valeur or '')
    chiffres = re.sub(r'^(\+221|00221)', '', chiffres)
    return chiffres if re.fullmatch(r'[37]\d{8}', chiffres) else None


class LoginForm(AuthenticationForm):
    """Connexion par numéro de téléphone (habitants) ou nom d'utilisateur (équipe)."""
    def clean_username(self):
        identifiant = self.cleaned_data.get('username', '').strip()
        tel = normaliser_telephone(identifiant)
        if tel:
            user = (CustomUser.objects.filter(username=tel).first()
                    or CustomUser.objects.filter(telephone=tel).first())
            if user:
                return user.username
        return identifiant

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': "Nom d'utilisateur"})
        self.fields['password'].widget.attrs.update({'placeholder': 'Mot de passe'})
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username', css_class='form-control form-control-lg'),
            Field('password', css_class='form-control form-control-lg'),
            Submit('submit', 'Se connecter', css_class='btn btn-primary btn-lg w-100 mt-3'),
        )


class RegisterForm(UserCreationForm):
    """Inscription d'un habitant : le numéro de téléphone sert d'identifiant de
    connexion et permet à l'équipe technique de le rappeler sur le terrain."""
    first_name = forms.CharField(max_length=100, required=True, label='Prénom')
    last_name = forms.CharField(max_length=100, required=True, label='Nom')
    telephone = forms.CharField(max_length=20, required=True, label='Numéro de téléphone')
    village = forms.ModelChoiceField(
        queryset=None, required=True, label='Village', empty_label='— Choisir votre village —',
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'telephone', 'village', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from commune.models import Village
        self.fields['village'].queryset = Village.objects.order_by('nom')
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('telephone'), Column('village')),
            'password1', 'password2',
            Submit('submit', 'Créer mon compte', css_class='btn btn-primary btn-lg w-100 mt-3'),
        )

    def clean_telephone(self):
        tel = normaliser_telephone(self.cleaned_data['telephone'])
        if not tel:
            raise forms.ValidationError('Numéro invalide : 9 chiffres commençant par 7 ou 3 (ex : 77 123 45 67).')
        if CustomUser.objects.filter(Q(username=tel) | Q(telephone=tel)).exists():
            raise forms.ValidationError('Un compte existe déjà avec ce numéro. Connectez-vous ou utilisez « Mot de passe oublié ».')
        # Connu avant la vérification du mot de passe : refuse un mot de passe égal au numéro.
        self.instance.username = tel
        return tel

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.telephone   # identifiant de connexion = téléphone
        # L'inscription libre est réservée aux habitants (signalement de problèmes) ;
        # les rôles UAD / communaux sont attribués par un administrateur.
        user.role = CustomUser.ROLE_CITOYEN
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'telephone', 'village', 'role', 'photo', 'is_active']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'telephone': 'Téléphone',
            'role': 'Rôle',
            'photo': 'Photo de profil',
            'is_active': 'Compte actif',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('email'), Column('telephone')),
            Row(Column('role'), Column('village')),
            'photo',
            'is_active',
            Row(
                Column(Submit('submit', 'Enregistrer', css_class='btn btn-primary')),
                Column(
                    '<a href="{% url \'accounts:users\' %}" class="btn btn-secondary">Annuler</a>',
                    css_class='col-auto'
                ),
            ),
        )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'telephone', 'village', 'photo']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'telephone': 'Téléphone',
            'photo': 'Photo de profil',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('email'), Column('telephone')),
            Row(Column('village'), Column('photo')),
            HTML('<div class="d-flex gap-2 mt-3">'),
            Submit('submit', 'Enregistrer les modifications', css_class='btn btn-primary'),
            HTML('<a href="{% url \'accounts:profile\' %}" class="btn btn-outline-secondary">Annuler</a></div>'),
        )
