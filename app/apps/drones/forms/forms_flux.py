from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, ButtonHolder, Column, Layout, Row, Submit
from django import forms

from ..models import FluxVideo


class FluxVideoImportForm(forms.ModelForm):
    class Meta:
        model = FluxVideo
        fields = ['nom', 'fichier', 'operateur']
        widgets = {
            'fichier': forms.FileInput(attrs={
                'accept': '.mp4,.mov,.avi,.mkv',
                'id': 'id_fichier_video',
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
