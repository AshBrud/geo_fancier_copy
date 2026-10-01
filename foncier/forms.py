from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, ButtonHolder, Button
from django.contrib.gis.forms import GeometryField as GeoFormField
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon, LineString, MultiLineString
from .models import Espace, Batiment, FonctionBatiment, SuiviTravaux, Terrain, EspaceVert, Voirie

GEO_WIDGET_ATTRS = {
    'class': 'form-control geom-input',
    'rows': 4,
    'placeholder': 'Collez le GeoJSON ici ou dessinez sur la carte...',
}


def _to_multipolygon(geom):
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=geom.srid or 4326)
    return geom


def _to_multilinestring(geom):
    if isinstance(geom, LineString):
        return MultiLineString(geom, srid=geom.srid or 4326)
    return geom


class EspaceForm(forms.ModelForm):
    # Champ géométrie générique : accepte Polygon ET MultiPolygon
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_espace'].choices = Espace.TYPES_SOUS_ESPACE
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
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'taux_occupation': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 100, 'step': 1,
            }),
        }

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
        widgets = {
            'nom':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Amphithéâtre A'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : BAT-001'}),
            'fonction': forms.Select(attrs={'class': 'form-select'}),
            'etages': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 20}),
            'annee_construction': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex : 2015'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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


class TerrainForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
    )

    class Meta:
        model = Terrain
        fields = ['nom', 'code', 'description', 'type_terrain', 'etat',
                  'photo', 'est_actif', 'observation', 'geometrie']
        labels = {
            'nom': 'Nom du terrain',
            'code': 'Code unique',
            'description': 'Description',
            'type_terrain': 'Type',
            'etat': 'État',
            'photo': 'Photo',
            'est_actif': 'Actif',
            'observation': 'Observation',
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Réserve foncière Nord'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : TER-001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'type_terrain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Terrain nu, Réserve foncière...'}),
            'etat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Bon, Dégradé, En friche...'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            'description',
            Row(Column('type_terrain', css_class='col-md-6'), Column('etat', css_class='col-md-6')),
            'photo', 'est_actif', 'observation', 'geometrie',
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


class EspaceVertForm(forms.ModelForm):
    geometrie = GeoFormField(
        widget=forms.Textarea(attrs=GEO_WIDGET_ATTRS),
        label='Géométrie (GeoJSON)',
        required=True,
    )

    class Meta:
        model = EspaceVert
        fields = ['nom', 'code', 'description', 'type_espace_vert', 'etat',
                  'photo', 'est_actif', 'observation', 'geometrie']
        labels = {
            'nom': "Nom de l'espace vert",
            'code': 'Code unique',
            'description': 'Description',
            'type_espace_vert': 'Type',
            'etat': 'État',
            'photo': 'Photo',
            'est_actif': 'Actif',
            'observation': 'Observation',
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Pelouse centrale'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : EV-001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'type_espace_vert': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Pelouse, Jardin, Zone plantée...'}),
            'etat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Entretenu, À rénover...'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('code', css_class='col-md-4')),
            'description',
            Row(Column('type_espace_vert', css_class='col-md-6'), Column('etat', css_class='col-md-6')),
            'photo', 'est_actif', 'observation', 'geometrie',
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
            'type_voirie': 'Type',
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
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )

    def clean_geometrie(self):
        geom = self.cleaned_data.get('geometrie')
        if geom is None:
            raise forms.ValidationError("Veuillez dessiner la géométrie sur la carte.")
        return _to_multilinestring(geom)


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


class SuiviTravauxForm(forms.ModelForm):
    class Meta:
        model = SuiviTravaux
        fields = ['maitre_ouvrage', 'statut', 'date_debut', 'date_fin_prevue', 'observations']
        widgets = {
            'maitre_ouvrage': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin_prevue': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
