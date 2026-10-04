from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, ButtonHolder, Column, Layout, Row, Submit
from django import forms

from ..models import Mission


class MissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = [
            'nom', 'date_vol', 'operateur', 'drone_utilise',
            'altitude', 'duree_minutes', 'superficie_prevue', 'notes',
        ]
        widgets = {
            'date_vol': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'altitude': "Altitude de vol (m)",
            'duree_minutes': "Durée du vol (min)",
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
