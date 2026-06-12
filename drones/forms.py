from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from .models import MissionDrone, Orthophoto


class MissionDroneForm(forms.ModelForm):
    class Meta:
        model = MissionDrone
        fields = ['nom', 'date_mission', 'operateur', 'drone_utilise',
                  'altitude_vol', 'recouvrement', 'statut', 'description']
        widgets = {
            'date_mission': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nom', css_class='col-md-8'), Column('date_mission', css_class='col-md-4')),
            Row(Column('operateur', css_class='col-md-6'), Column('drone_utilise', css_class='col-md-6')),
            Row(Column('altitude_vol', css_class='col-md-4'),
                Column('recouvrement', css_class='col-md-4'),
                Column('statut', css_class='col-md-4')),
            'description',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )


class OrthophotoForm(forms.ModelForm):
    class Meta:
        model = Orthophoto
        fields = ['mission', 'nom', 'fichier', 'date_prise', 'resolution', 'description']
        widgets = {
            'date_prise': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('mission', css_class='col-md-8'), Column('date_prise', css_class='col-md-4')),
            Row(Column('nom', css_class='col-md-8'), Column('resolution', css_class='col-md-4')),
            'fichier', 'description',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )
