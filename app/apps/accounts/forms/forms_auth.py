from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field
from accounts.models import CustomUser


class LoginForm(AuthenticationForm):
    """
    Formulaire d'authentification institutionnel épuré.
    Prend en charge la connexion par nom d'utilisateur ou par téléphone.
    """
    def clean_username(self):
        identifiant = self.cleaned_data.get('username', '').strip()
        user = (
            CustomUser.objects.filter(username=identifiant).first()
            or CustomUser.objects.filter(email__iexact=identifiant).first()
            or CustomUser.objects.filter(telephone=identifiant).first()
        )
        if user:
            return user.username
        return identifiant

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': "Identifiant ou email"})
        self.fields['password'].widget.attrs.update({'placeholder': "Mot de passe"})
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username', css_class='form-control form-control-lg'),
            Field('password', css_class='form-control form-control-lg'),
            Submit('submit', 'Se connecter', css_class='btn btn-primary btn-lg w-100 mt-3'),
        )
