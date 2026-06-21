from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from .models import Orthophoto


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
