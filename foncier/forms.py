from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from .models import Espace, Batiment, FonctionBatiment

GEO_WIDGET_ATTRS = {
    'class': 'form-control geom-input',
    'rows': 4,
    'placeholder': 'Collez le GeoJSON ici ou dessinez sur la carte...',
}


def _to_multipolygon(geom):
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=geom.srid or 4326)
    return geom


class EspaceForm(forms.ModelForm):
    # Champ géométrie générique : accepte Polygon ET MultiPolygon
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
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
            'taux_occupation': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1, 'max': 100, 'step': 1,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            Row(Column('type_espace', css_class='col-md-6'), Column('taux_occupation', css_class='col-md-3'), Column('usage', css_class='col-md-3')),
            'description',
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez dessiner la géométrie sur la carte.")
        return _to_multipolygon(geom)


class BatimentForm(forms.ModelForm):
    # Champ géométrie générique : accepte Polygon ET MultiPolygon
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

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez dessiner la géométrie sur la carte.")
        return _to_multipolygon(geom)
