"""
Formulaires pour les signalements d'incidents (SignalementDommage).
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from dossiers.models import SignalementDommage, ZoneSecteur
from .forms_common import GEO_WIDGET_ATTRS
from ..services.services_signalement import to_point


class SignalementDommageForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Localisation GPS (Point GeoJSON WGS 84)',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        dossier = kwargs.pop('dossier', None)
        super().__init__(*args, **kwargs)

        if dossier:
            self.fields['zone_secteur'].queryset = ZoneSecteur.objects.filter(dossier=dossier).order_by('nom')
        else:
            self.fields['zone_secteur'].queryset = ZoneSecteur.objects.none()

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'titre',
            Row(
                Column('categorie', css_class='col-md-6'),
                Column('priorite', css_class='col-md-6'),
            ),
            'zone_secteur',
            'description',
            'photo',
            'geometrie',
            ButtonHolder(
                Submit('submit', 'Déclarer le signalement', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2', data_bs_dismiss='modal'),
            )
        )

    class Meta:
        model = SignalementDommage
        fields = [
            'titre', 'categorie', 'priorite', 'zone_secteur',
            'description', 'photo', 'geometrie',
        ]
        labels = {
            'titre': "Intitulé succinct de l'anomalie",
            'categorie': "Nature du dommage",
            'priorite': "Niveau de priorité",
            'zone_secteur': "Zone / Localité concernée",
            'description': "Description détaillée du problème",
            'photo': "Photographie du constat",
        }
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Fuite d\'eau canalisation principale...'}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'priorite': forms.Select(attrs={'class': 'form-select'}),
            'zone_secteur': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez marquer l'emplacement exact de l'incident sur la carte.")
        return to_point(geom)


class ChangementStatutDommageForm(forms.Form):
    nouveau_statut = forms.ChoiceField(
        choices=SignalementDommage.STATUTS,
        label="Nouveau statut opérationnel",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    commentaire = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Motif du changement ou compte-rendu d\'intervention…'}),
        label="Rapport / Commentaire d'intervention"
    )
