from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button, HTML, Fieldset
from .models import MissionDrone, Orthophoto


class MissionDroneForm(forms.ModelForm):
    class Meta:
        model  = MissionDrone
        fields = ['nom', 'date_mission', 'operateur', 'drone_utilise',
                  'altitude_vol', 'recouvrement', 'statut', 'description',
                  'tiles_url', 'fichier_kml']
        widgets = {
            'date_mission': forms.DateInput(attrs={'type': 'date'}),
            'description':  forms.Textarea(attrs={'rows': 3}),
            'tiles_url':    forms.TextInput(attrs={
                'placeholder': '/static/tiles/mission/{z}/{x}/{y}.png'
            }),
            'fichier_kml': forms.FileInput(attrs={'accept': '.kml,.kmz,.gpx'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tiles_url'].required   = False
        self.fields['fichier_kml'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Informations générales',
                Row(Column('nom', css_class='col-md-8'), Column('date_mission', css_class='col-md-4')),
                Row(Column('operateur', css_class='col-md-6'), Column('drone_utilise', css_class='col-md-6')),
            ),
            Fieldset(
                'Paramètres de vol',
                Row(
                    Column('altitude_vol',  css_class='col-md-4'),
                    Column('recouvrement', css_class='col-md-4'),
                    Column('statut',       css_class='col-md-4'),
                ),
                'description',
            ),
            Fieldset(
                'Zone couverte — import automatique',
                HTML('''<p class="text-muted small mb-3">
                    <i class="bi bi-geo-alt me-1"></i>
                    Importez un fichier <strong>KML, KMZ ou GPX</strong> pour définir automatiquement
                    la zone couverte par la mission. Le premier polygone trouvé sera utilisé.
                </p>'''),
                'fichier_kml',
            ),
            Fieldset(
                'Intégration cartographique (WebODM)',
                HTML('''<p class="text-muted small mb-3">
                    <i class="bi bi-info-circle me-1"></i>
                    Après traitement WebODM, exportez les tuiles XYZ dans
                    <code>static/tiles/nom_mission/</code> et renseignez l\'URL ci-dessous.
                </p>'''),
                'tiles_url',
            ),
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary px-4'),
                Button('cancel', 'Annuler', css_class='btn btn-light ms-2',
                       onclick='window.history.back()'),
            )
        )


class OrthophotoImportForm(forms.ModelForm):
    class Meta:
        model  = Orthophoto
        fields = ['mission', 'nom', 'fichier', 'date_prise', 'resolution', 'emprise', 'description']
        widgets = {
            'date_prise':  forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'fichier':     forms.FileInput(attrs={
                'accept': '.tif,.tiff,.geotiff,.png,.jpg,.jpeg',
                'id':     'id_fichier_ortho',
            }),
            'emprise':     forms.HiddenInput(),
        }
        labels = {
            'fichier': 'Fichier orthophoto (GeoTIFF, PNG, JPEG)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolution'].required  = False
        self.fields['emprise'].required     = False
        self.fields['description'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('mission', css_class='col-md-8'), Column('date_prise', css_class='col-md-4')),
            Row(Column('nom', css_class='col-md-8'), Column('resolution', css_class='col-md-4')),
            'fichier',
            'emprise',
            'description',
            ButtonHolder(
                Submit('submit', "Importer l'orthophoto", css_class='btn btn-success px-4'),
                Button('cancel', 'Annuler', css_class='btn btn-light ms-2',
                       onclick='window.history.back()'),
            )
        )
