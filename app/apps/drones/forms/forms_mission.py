from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, ButtonHolder, Column, Layout, Row, Submit
from django import forms
from django.contrib.gis.forms import GeometryField as GeoFormField
from django.contrib.gis.geos import GEOSGeometry, Polygon, LineString

from ..models import Mission


class MissionForm(forms.ModelForm):
    emprise = GeoFormField(
        widget=forms.HiddenInput(attrs={'id': 'id_mission_emprise'}),
        required=False,
        label='Limites de vol (GeoJSON)',
    )
    trajectoire = GeoFormField(
        widget=forms.HiddenInput(attrs={'id': 'id_mission_trajectoire'}),
        required=False,
        label='Trajectoire de vol (GeoJSON)',
    )

    class Meta:
        model = Mission
        fields = [
            'nom', 'date_vol', 'operateur', 'drone_utilise',
            'altitude', 'duree_minutes', 'superficie_prevue',
            'emprise', 'trajectoire', 'notes',
        ]
        widgets = {
            'date_vol': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes et consignes opérationnelles de vol...'}),
        }
        labels = {
            'altitude': "Altitude de vol (m)",
            'duree_minutes': "Durée du vol (min)",
            'superficie_prevue': "Superficie prévue (ha)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in ('drone_utilise', 'altitude', 'duree_minutes', 'superficie_prevue', 'operateur', 'notes', 'emprise', 'trajectoire'):
            if champ in self.fields:
                self.fields[champ].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('date_vol', css_class='col-md-4')),
            Row(Column('operateur', css_class='col-md-6'), Column('drone_utilise', css_class='col-md-6')),
            Row(
                Column('altitude', css_class='col-md-4'),
                Column('duree_minutes', css_class='col-md-4'),
                Column('superficie_prevue', css_class='col-md-4'),
            ),
            'notes',
            'emprise',
            'trajectoire',
        )

    def clean_emprise(self):
        geom = self.cleaned_data.get('emprise')
        if not geom:
            return None
        if isinstance(geom, Polygon):
            return geom
        if hasattr(geom, 'geom_type') and geom.geom_type == 'MultiPolygon':
            return geom[0]
        return geom

    def clean_trajectoire(self):
        geom = self.cleaned_data.get('trajectoire')
        if not geom:
            return None
        if isinstance(geom, LineString):
            return geom
        if hasattr(geom, 'geom_type') and geom.geom_type == 'MultiLineString':
            return geom[0]
        return geom
