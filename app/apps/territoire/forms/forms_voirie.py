from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from territoire.models import Voirie
from .forms_common import GEO_WIDGET_ATTRS, to_multilinestring


class VoirieForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
    )

    class Meta:
        model = Voirie
        fields = ['nom', 'code', 'description', 'type_voirie', 'revetement', 'etat',
                  'photo', 'est_actif', 'observation', 'geometrie']
        labels = {
            'nom': 'Nom de la voirie',
            'code': 'Code unique',
            'description': 'Description',
            'type_voirie': 'Type de voirie',
            'revetement': 'Revêtement',
            'etat': 'État',
            'photo': 'Photo',
            'est_actif': 'Actif',
            'observation': 'Observation',
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Allée centrale'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : VOI-001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'type_voirie': forms.Select(attrs={'class': 'form-select'}),
            'revetement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Bitume, Pavé, Terre...'}),
            'etat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Bon, Dégradé...'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            'description',
            Row(Column('type_voirie', css_class='col-md-4'), Column('revetement', css_class='col-md-4'), Column('etat', css_class='col-md-4')),
            'photo', 'est_actif', 'observation', 'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez renseigner ou tracer le tracé de la voie.")
        return to_multilinestring(geom)
