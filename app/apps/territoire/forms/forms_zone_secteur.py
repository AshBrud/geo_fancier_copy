"""
Formulaire pour les subdivisions territoriales (ZoneSecteur).
Prise en charge du dessin cartographique GeoJSON, validation WGS84 et conversion MultiPolygon.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from dossiers.models import ZoneSecteur
from .forms_common import GEO_WIDGET_ATTRS, to_multipolygon


class ZoneSecteurForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Emprise spatiale (GeoJSON WGS 84)',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        dossier = kwargs.pop('dossier', None)
        super().__init__(*args, **kwargs)

        if dossier:
            # Si le dossier est de type université, restreindre ou ordonner les choix
            if dossier.type_territoire == 'universite':
                self.fields['type_zone'].initial = ZoneSecteur.TYPE_SECTEUR_CAMPUS
            elif dossier.type_territoire == 'commune':
                self.fields['type_zone'].initial = ZoneSecteur.TYPE_VILLAGE

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nom', css_class='col-md-8'),
                Column('code', css_class='col-md-4'),
            ),
            Row(
                Column('type_zone', css_class='col-md-6'),
                Column('statut', css_class='col-md-6'),
            ),
            Row(
                Column('responsable_nom', css_class='col-md-6'),
                Column('responsable_telephone', css_class='col-md-6'),
            ),
            'description',
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer la zone', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    class Meta:
        model = ZoneSecteur
        fields = [
            'nom', 'code', 'type_zone', 'statut',
            'responsable_nom', 'responsable_telephone',
            'description', 'geometrie',
        ]
        labels = {
            'nom': "Désignation de la zone ou localité",
            'code': "Identifiant unique (laisser vide pour auto)",
            'type_zone': "Nature de la subdivision",
            'statut': "Statut d'aménagement",
            'responsable_nom': "Responsable / Référent",
            'responsable_telephone': "Contact téléphonique",
            'description': "Notes & Contexte",
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Secteur Pédagogique Nord, Village de Ngogom...'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : SEC-01, V-001 (optionnel)'}),
            'type_zone': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'responsable_nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du délégué ou chef de village'}),
            'responsable_telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+221 77 ...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez tracer ou renseigner la géométrie de la zone.")
        return to_multipolygon(geom)
