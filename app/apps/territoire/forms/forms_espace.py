from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from territoire.models import Espace
from .forms_common import GEO_WIDGET_ATTRS, to_multipolygon


class EspaceForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_espace'].choices = Espace.TYPES_SOUS_ESPACE
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            Row(Column('type_espace', css_class='col-md-6'), Column('taux_occupation', css_class='col-md-3'), Column('usage', css_class='col-md-3')),
            'description',
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    class Meta:
        model = Espace
        fields = ['nom', 'code', 'type_espace', 'taux_occupation', 'description', 'usage', 'geometrie']
        labels = {
            'nom': "Nom de l'espace",
            'code': 'Code unique',
            'type_espace': "Type d'espace",
            'taux_occupation': "Taux d'occupation max (%)",
            'description': 'Description',
            'usage': 'Usage actuel',
        }
        widgets = {
            'nom':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Zone pédagogique Nord'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : ESP-001'}),
            'usage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Amphithéâtres, salles de cours...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'taux_occupation': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 100, 'step': 1,
            }),
        }

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez renseigner ou dessiner la géométrie de l'espace.")
        return to_multipolygon(geom)
