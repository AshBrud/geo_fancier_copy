from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from territoire.models import Batiment
from .forms_common import GEO_WIDGET_ATTRS, to_multipolygon


class BatimentForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
    )

    class Meta:
        model = Batiment
        fields = ['nom', 'code', 'fonction', 'etages', 'annee_construction',
                  'description', 'photo', 'est_actif', 'geometrie']
        labels = {
            'nom': 'Nom du bâtiment',
            'code': 'Code unique',
            'fonction': 'Fonction principale',
            'etages': "Nombre d'étages",
            'annee_construction': 'Année de construction',
            'description': 'Description',
            'photo': 'Photo',
            'est_actif': 'Bâtiment actif',
        }
        widgets = {
            'nom':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Amphithéâtre A'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : BAT-001'}),
            'fonction': forms.Select(attrs={'class': 'form-select'}),
            'etages': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 20}),
            'annee_construction': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex : 2015'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            Row(Column('fonction', css_class='col-md-6'), Column('etages', css_class='col-md-3'),
                Column('annee_construction', css_class='col-md-3')),
            Row(Column('est_actif', css_class='col-md-4')),
            'description', 'photo', 'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez renseigner ou dessiner l'emprise du bâtiment.")
        return to_multipolygon(geom)


class BatimentImportForm(forms.Form):
    fichier = forms.FileField(
        label='Fichier SIG (GeoJSON, GPKG, Shapefile...)',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.geojson,.json,.gpkg,.shp,.zip',
        }),
    )
    source_crs = forms.CharField(
        label='Projection source (si absente du fichier)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Ex : EPSG:32628',
        }),
    )
    dry_run = forms.BooleanField(
        label='Prévisualiser seulement (sans écrire en base)',
        required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'fichier',
            'source_crs',
            'dry_run',
            ButtonHolder(
                Submit('submit', 'Analyser / Importer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )
