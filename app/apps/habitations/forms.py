from django import forms
from django.contrib.gis.forms import GeometryField as GeoFormField
from django.contrib.gis.geos import LineString, MultiLineString, MultiPolygon, Point, Polygon

from .models import Commune, Maison, Piste, Signalement, Village

GEO_WIDGET_ATTRS = {
    'class': 'form-control geom-input',
    'rows': 3,
    'placeholder': 'Collez le GeoJSON ici ou dessinez sur la carte...',
}


def _champ_geometrie(label):
    return GeoFormField(widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS), label=label, required=True)


class _GeoJSONInitialMixin:
    """Pré-remplit le champ géométrie en GeoJSON (et non en WKT) pour que la
    carte du formulaire puisse réafficher la forme existante en modification."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.geometrie:
            self.initial['geometrie'] = self.instance.geometrie.geojson


class _PolygoneMixin(_GeoJSONInitialMixin):
    """Accepte un Polygon dessiné sur la carte et le stocke en MultiPolygon."""

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if isinstance(geom, Polygon):
            return MultiPolygon(geom, srid=geom.srid or 4326)
        if not isinstance(geom, MultiPolygon):
            raise forms.ValidationError("Veuillez dessiner un polygone sur la carte.")
        return geom


def _text(placeholder=''):
    return forms.TextInput(attrs={'class': 'form-control', 'placeholder': placeholder})


def _select():
    return forms.Select(attrs={'class': 'form-select'})


class CommuneForm(_PolygoneMixin, forms.ModelForm):
    geometrie = _champ_geometrie('Limite communale (GeoJSON)')

    class Meta:
        model = Commune
        fields = ['nom', 'departement', 'region', 'geometrie']
        widgets = {'nom': _text('Ex : Ngogom'), 'departement': _text(), 'region': _text()}


class VillageForm(_PolygoneMixin, forms.ModelForm):
    geometrie = _champ_geometrie('Limites du village (GeoJSON)')

    class Meta:
        model = Village
        fields = ['nom', 'code', 'geometrie']
        widgets = {'nom': _text('Ex : Ngogom Keur Samba'), 'code': _text('Automatique si vide')}


class MaisonForm(_PolygoneMixin, forms.ModelForm):
    geometrie = _champ_geometrie('Emprise de la maison (GeoJSON)')

    class Meta:
        model = Maison
        fields = ['village', 'code', 'statut_occupation', 'geometrie']
        widgets = {
            'village': _select(),
            'code': _text('Automatique si vide'),
            'statut_occupation': forms.RadioSelect,
        }


class PisteForm(_GeoJSONInitialMixin, forms.ModelForm):
    geometrie = _champ_geometrie('Tracé (GeoJSON)')

    class Meta:
        model = Piste
        fields = ['nom', 'type_voie', 'geometrie']
        widgets = {'nom': _text('Ex : Piste Ngogom – Bambey'), 'type_voie': _select()}

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if isinstance(geom, LineString):
            return MultiLineString(geom, srid=geom.srid or 4326)
        if not isinstance(geom, MultiLineString):
            raise forms.ValidationError("Veuillez tracer une ligne sur la carte.")
        return geom


class SignalementForm(_GeoJSONInitialMixin, forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.HiddenInput, required=True, label='Localisation',
        error_messages={'required': "Indiquez l'emplacement du problème sur la carte (ou utilisez « Ma position »)."},
    )

    class Meta:
        model = Signalement
        fields = ['categorie', 'titre', 'village', 'description', 'priorite', 'photo', 'geometrie']
        widgets = {
            'categorie': forms.RadioSelect,
            'titre': _text("Ex : Tuyau d'eau cassé"),
            'village': _select(),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                 'placeholder': 'Décrivez le problème : depuis quand, gravité, repère…'}),
            'priorite': _select(),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['village'].empty_label = '— Détecter automatiquement depuis la carte —'
        self.fields['categorie'].choices = Signalement.CATEGORIES  # pas d'option vide « --------- »

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if not isinstance(geom, Point):
            raise forms.ValidationError("Indiquez l'emplacement du problème par un point sur la carte.")
        return geom


class ChangementStatutForm(forms.Form):
    nouveau_statut = forms.ChoiceField(label='Nouveau statut', widget=forms.Select(attrs={'class': 'form-select'}))
    commentaire = forms.CharField(
        label='Commentaire (optionnel)', required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Équipe technique envoyée'}),
    )

    def __init__(self, signalement, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nouveau_statut'].choices = signalement.statuts_suivants()
