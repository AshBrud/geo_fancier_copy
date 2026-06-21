from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from .models import NouvelleConstruction, HistoriqueConstruction


class NouvelleConstructionForm(forms.ModelForm):
    class Meta:
        model = NouvelleConstruction
        fields = ['nom_projet', 'type_construction', 'superficie_souhaitee']
        labels = {
            'nom_projet': 'Nom du projet',
            'type_construction': 'Type de construction',
            'superficie_souhaitee': 'Superficie souhaitée (m²)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'nom_projet',
            Row(Column('type_construction', css_class='col-md-7'),
                Column('superficie_souhaitee', css_class='col-md-5')),
            ButtonHolder(
                Submit('submit', 'Analyser la disponibilité', css_class='btn btn-primary w-100'),
            )
        )

    def clean_superficie_souhaitee(self):
        superficie = self.cleaned_data.get('superficie_souhaitee')
        if superficie is None:
            return superficie
        if superficie <= 0:
            raise forms.ValidationError("La superficie souhaitée doit être supérieure à 0 m².")
        if superficie > 520000:
            raise forms.ValidationError(
                "La superficie souhaitée ne peut pas dépasser 520 000 m² (52 ha, superficie du campus UAD)."
            )
        return superficie


class HistoriqueConstructionForm(forms.ModelForm):
    class Meta:
        model = HistoriqueConstruction
        fields = ['batiment', 'type_travaux', 'date_debut', 'date_fin',
                  'description', 'cout', 'maitre_ouvrage']
        labels = {
            'batiment': 'Bâtiment concerné',
            'type_travaux': 'Type de travaux',
            'date_debut': 'Date de début',
            'date_fin': 'Date de fin',
            'cout': 'Coût estimé (FCFA)',
            'maitre_ouvrage': 'Maître d\'ouvrage',
        }
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('batiment', css_class='col-md-6'), Column('type_travaux', css_class='col-md-6')),
            Row(Column('date_debut', css_class='col-md-4'), Column('date_fin', css_class='col-md-4'),
                Column('cout', css_class='col-md-4')),
            'maitre_ouvrage', 'description',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )
