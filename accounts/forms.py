from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, HTML
from .models import CustomUser


class LoginForm(AuthenticationForm):
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
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True, label='Prénom')
    last_name = forms.CharField(max_length=100, required=True, label='Nom')

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            'username', 'email', 'password1', 'password2',
            Submit('submit', 'Créer mon compte', css_class='btn btn-primary btn-lg w-100 mt-3'),
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.ROLE_OBSERVATEUR
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'telephone', 'role', 'photo', 'is_active']
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
            Row(Column('role'), Column('photo')),
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
        fields = ['first_name', 'last_name', 'email', 'telephone', 'photo']
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
            'photo',
            HTML('<div class="d-flex gap-2 mt-3">'),
            Submit('submit', 'Enregistrer les modifications', css_class='btn btn-primary'),
            HTML('<a href="{% url \'accounts:profile\' %}" class="btn btn-outline-secondary">Annuler</a></div>'),
        )
