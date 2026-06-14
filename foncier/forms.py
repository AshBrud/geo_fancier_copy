from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, ButtonHolder, Button
from .models import Espace, Batiment, FonctionBatiment



class EspaceForm(forms.ModelForm):
    class Meta:
        model = Espace
        fields = ['nom', 'code', 'type_espace', 'description', 'usage', 'geometrie']
        labels = {
            'nom': 'Nom de l\'espace',
            'code': 'Code unique',
            'type_espace': 'Type d\'espace',
            'description': 'Description',
            'usage': 'Usage actuel',
            'geometrie': 'Géométrie (GeoJSON)',
        }
        widgets = {
            'geometrie': forms.Textarea(attrs={
                'class': 'form-control geom-input',
                'rows': 4,
                'placeholder': 'Collez le GeoJSON ici ou dessinez sur la carte...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            Row(Column('type_espace', css_class='col-md-6'), Column('usage', css_class='col-md-6')),
            'description',
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )


class BatimentForm(forms.ModelForm):
    class Meta:
        model = Batiment
        fields = ['nom', 'code', 'fonction', 'etages', 'annee_construction',
                  'description', 'photo', 'est_actif', 'geometrie']
        labels = {
            'nom': 'Nom du bâtiment',
            'code': 'Code unique',
            'fonction': 'Fonction principale',
            'etages': 'Nombre d\'étages',
            'annee_construction': 'Année de construction',
            'capacite': 'Capacité (personnes)',
            'description': 'Description',
            'photo': 'Photo',
            'est_actif': 'Bâtiment actif',
            'geometrie': 'Géométrie (GeoJSON)',
        }
        widgets = {
            'geometrie': forms.Textarea(attrs={
                'class': 'form-control geom-input',
                'rows': 4,
                'placeholder': 'Collez le GeoJSON ici ou dessinez sur la carte...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            Row(Column('fonction', css_class='col-md-6'), Column('etages', css_class='col-md-3'),
                Column('annee_construction', css_class='col-md-3')),
            Row(Column('est_actif', css_class='col-md-4')),
            'description', 'photo', 'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )
