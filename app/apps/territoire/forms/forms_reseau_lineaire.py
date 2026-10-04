"""
Formulaire pour les réseaux linéaires et voiries (ReseauLineaire).
Support du tracé linéaire cartographique WGS84 et validation SIG.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from dossiers.models import ReseauLineaire
from .forms_common import GEO_WIDGET_ATTRS, to_multilinestring


class ReseauLineaireForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Tracé géographique (GeoJSON WGS 84)',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        dossier = kwargs.pop('dossier', None)
        super().__init__(*args, **kwargs)

        if dossier:
            if dossier.type_territoire == 'universite':
                self.fields['type_voie'].initial = ReseauLineaire.TYPE_ALLEE_PIETONNE
            elif dossier.type_territoire == 'commune':
                self.fields['type_voie'].initial = ReseauLineaire.TYPE_PISTE

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nom', css_class='col-md-8'),
                Column('code', css_class='col-md-4'),
            ),
            Row(
                Column('type_voie', css_class='col-md-6'),
                Column('etat_chaussee', css_class='col-md-6'),
            ),
            Row(
                Column('largeur_estimee_m', css_class='col-md-6'),
                Column('description', css_class='col-md-6'),
            ),
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Enregistrer le tracé', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    class Meta:
        model = ReseauLineaire
        fields = [
            'nom', 'code', 'type_voie', 'largeur_estimee_m',
            'etat_chaussee', 'description', 'geometrie',
        ]
        labels = {
            'nom': "Désignation de la voie ou du tronçon",
            'code': "Identifiant technique (auto si vide)",
            'type_voie': "Nature de l'infrastructure",
            'largeur_estimee_m': "Largeur approximative de la chaussée (m)",
            'etat_chaussee': "État de praticabilité (bon, moyen, dégradé)",
            'description': "Observations & Notes techniques",
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Boulevard Central, Piste Ngogom-Est...'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: LIN-004'}),
            'type_voie': forms.Select(attrs={'class': 'form-select'}),
            'largeur_estimee_m': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'etat_chaussee': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bon état, Praticable en saison sèche...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez tracer la ligne directrice sur la carte.")
        return to_multilinestring(geom)
