from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML
from accounts.models import CustomUser, Role, Permission


class AdminCreationForm(forms.Form):
    """
    Formulaire souverain de création d'un Administrateur Territorial.
    Accessible exclusivement par le Superuser racine.
    """
    username = forms.CharField(max_length=150, required=True, label="Identifiant de connexion")
    email = forms.EmailField(required=True, label="Adresse email professionnelle")
    first_name = forms.CharField(max_length=150, required=True, label="Prénom")
    last_name = forms.CharField(max_length=150, required=True, label="Nom")
    telephone = forms.CharField(max_length=30, required=False, label="Téléphone professionnel")
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
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('username'), Column('email')),
            Row(Column('telephone')),
            Row(Column('password'), Column('confirm_password')),
            HTML('<div class="d-flex justify-content-end gap-2 mt-4">'),
            HTML('<a href="{% url \'accounts:users\' %}" class="btn btn-outline-secondary">Annuler</a>'),
            Submit('submit', 'Créer l\'Administrateur', css_class='btn btn-primary px-4'),
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
