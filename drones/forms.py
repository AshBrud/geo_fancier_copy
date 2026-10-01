from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from .models import Orthophoto, Mission, FluxVideo


class MissionForm(forms.ModelForm):
    class Meta:
        model  = Mission
        fields = [
            'nom', 'date_vol', 'operateur', 'drone_utilise',
            'altitude', 'duree_minutes', 'superficie_prevue', 'notes',
        ]
        widgets = {
            'date_vol': forms.DateInput(attrs={'type': 'date'}),
            'notes':    forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'altitude':          "Altitude de vol (m)",
            'duree_minutes':     "Durée du vol (min)",
            'superficie_prevue': "Superficie prévue (ha)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in ('drone_utilise', 'altitude', 'duree_minutes', 'superficie_prevue', 'operateur', 'notes'):
            self.fields[champ].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('date_vol', css_class='col-md-4')),
            Row(Column('operateur', css_class='col-md-6'), Column('drone_utilise', css_class='col-md-6')),
            Row(
                Column('altitude', css_class='col-md-4'),
                Column('duree_minutes', css_class='col-md-4'),
                Column('superficie_prevue', css_class='col-md-4'),
            ),
            'notes',
            ButtonHolder(
                Submit('submit', 'Enregistrer la mission', css_class='btn btn-success px-4'),
                Button('cancel', 'Annuler', css_class='btn btn-light ms-2',
                       onclick='window.history.back()'),
            )
        )


class OrthophotoImportForm(forms.ModelForm):
    class Meta:
        model  = Orthophoto
        fields = ['nom', 'fichier', 'operateur', 'resolution', 'emprise', 'tiles_url', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'fichier':     forms.FileInput(attrs={
                'accept': '.tif,.tiff,.geotiff,.png,.jpg,.jpeg',
                'id':     'id_fichier_ortho',
            }),
            'emprise':   forms.HiddenInput(),
            'tiles_url': forms.TextInput(attrs={
                'placeholder': '/static/tiles/{z}/{x}/{y}.png'
            }),
        }
        labels = {
            'fichier':    'Fichier orthophoto (GeoTIFF, PNG, JPEG)',
            'tiles_url':  'URL tuiles XYZ (WebODM)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolution'].required  = False
        self.fields['emprise'].required     = False
        self.fields['description'].required = False
        self.fields['operateur'].required   = False
        self.fields['tiles_url'].required   = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('operateur', css_class='col-md-4')),
            Row(Column('resolution', css_class='col-md-6')),
            'fichier',
            'emprise',
            'tiles_url',
            'description',
            ButtonHolder(
                Submit('submit', "Importer l'orthophoto", css_class='btn btn-success px-4'),
                Button('cancel', 'Annuler', css_class='btn btn-light ms-2',
                       onclick='window.history.back()'),
            )
        )


class FluxVideoImportForm(forms.ModelForm):
    class Meta:
        model  = FluxVideo
        fields = ['nom', 'fichier', 'operateur']
        widgets = {
            'fichier': forms.FileInput(attrs={
                'accept': '.mp4,.mov,.avi,.mkv',
                'id':     'id_fichier_video',
            }),
        }
        labels = {
            'fichier': 'Fichier vidéo (MP4, MOV, AVI, MKV)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operateur'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('operateur', css_class='col-md-4')),
            'fichier',
            ButtonHolder(
                Submit('submit', 'Importer la vidéo', css_class='btn btn-success px-4'),
                Button('cancel', 'Annuler', css_class='btn btn-light ms-2',
                       onclick='window.history.back()'),
            )
        )
