"""
Formulaire pour le recensement bâti unifié (UniteBatie).
Support du tracé cartographique WGS84, validation SIG et assignation au Dossier actif.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from dossiers.models import UniteBatie, ZoneSecteur
from .forms_common import GEO_WIDGET_ATTRS, to_multipolygon


class UniteBatieForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Emprise au sol (GeoJSON WGS 84)',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        dossier = kwargs.pop('dossier', None)
        super().__init__(*args, **kwargs)

        if dossier:
            self.fields['zone_secteur'].queryset = ZoneSecteur.objects.filter(dossier=dossier).order_by('nom')
            if dossier.type_territoire == 'universite':
                self.fields['type_bati'].initial = UniteBatie.TYPE_PEDAGOGIQUE
            elif dossier.type_territoire == 'commune':
                self.fields['type_bati'].initial = UniteBatie.TYPE_HABITATION
        else:
            self.fields['zone_secteur'].queryset = ZoneSecteur.objects.none()

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nom', css_class='col-md-8'),
                Column('code', css_class='col-md-4'),
            ),
            Row(
                Column('type_bati', css_class='col-md-6'),
                Column('statut_occupation', css_class='col-md-6'),
            ),
            Row(
                Column('zone_secteur', css_class='col-md-6'),
                Column('etages', css_class='col-md-3'),
                Column('annee_construction', css_class='col-md-3'),
            ),
            Row(
                Column('photo', css_class='col-md-8'),
                Column('est_actif', css_class='col-md-4 pt-4'),
            ),
            'description',
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer l\'unité bâtie', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    class Meta:
        model = UniteBatie
        fields = [
            'nom', 'code', 'type_bati', 'statut_occupation',
            'zone_secteur', 'etages', 'annee_construction',
            'photo', 'est_actif', 'description', 'geometrie',
        ]
        labels = {
            'nom': "Désignation ou nom de la concession / édifice",
            'code': "Code répertoire unique (auto si vide)",
            'type_bati': "Typologie / Usage principal",
            'statut_occupation': "Statut d'occupation",
            'zone_secteur': "Zone / Subdivision de rattachement",
            'etages': "Nombre de niveaux (R+N)",
            'annee_construction': "Année d'édification",
            'photo': "Cliché photographique",
            'est_actif': "Bâtiment existant et actif",
            'description': "Observations & Notes techniques",
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bâtiment Recherche, Concession Diagne...'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: BAT-0012, M-0045'}),
            'type_bati': forms.Select(attrs={'class': 'form-select'}),
            'statut_occupation': forms.Select(attrs={'class': 'form-select'}),
            'zone_secteur': forms.Select(attrs={'class': 'form-select'}),
            'etages': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
            'annee_construction': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2018'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez tracer ou fournir l'emprise polygonale du bâtiment.")
        return to_multipolygon(geom)
