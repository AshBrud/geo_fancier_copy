from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, ButtonHolder, Button
from constructions.models.models_construction import NouvelleConstruction, HistoriqueConstruction


class NouvelleConstructionForm(forms.ModelForm):
    class Meta:
        model = NouvelleConstruction
        fields = ['nom_projet', 'type_construction', 'superficie_souhaitee', 'zone_secteur']
        labels = {
            'nom_projet': 'Nom du projet',
            'type_construction': 'Type de construction',
            'superficie_souhaitee': 'Superficie souhaitée (m²)',
            'zone_secteur': 'Zone ou secteur cible',
        }

    def __init__(self, *args, dossier=None, **kwargs):
        super().__init__(*args, **kwargs)
        if dossier:
            self.fields['zone_secteur'].queryset = self.fields['zone_secteur'].queryset.filter(dossier=dossier)
        else:
            self.fields['zone_secteur'].required = False

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'nom_projet',
            Row(
                Column('type_construction', css_class='col-md-6'),
                Column('superficie_souhaitee', css_class='col-md-6')
            ),
            'zone_secteur',
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
        fields = [
            'batiment', 'unite_batie', 'type_travaux', 'date_debut', 'date_fin',
            'description', 'cout', 'maitre_ouvrage'
        ]
        labels = {
            'batiment': 'Bâtiment concerné (Campus)',
            'unite_batie': 'Unité bâtie concernée (V2)',
            'type_travaux': 'Type de travaux',
            'date_debut': 'Date de début',
            'date_fin': 'Date de fin',
            'cout': 'Coût estimé (FCFA)',
            'maitre_ouvrage': 'Maître d\'ouvrage / Prestataire',
        }
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, dossier=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batiment'].required = False
        self.fields['unite_batie'].required = False

        if dossier:
            self.fields['unite_batie'].queryset = self.fields['unite_batie'].queryset.filter(dossier=dossier)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('batiment', css_class='col-md-6'),
                Column('unite_batie', css_class='col-md-6')
            ),
            Row(
                Column('type_travaux', css_class='col-md-6'),
                Column('maitre_ouvrage', css_class='col-md-6')
            ),
            Row(
                Column('date_debut', css_class='col-md-4'),
                Column('date_fin', css_class='col-md-4'),
                Column('cout', css_class='col-md-4')
            ),
            'description',
            ButtonHolder(
                Submit('submit', 'Enregistrer', css_class='btn btn-primary'),
                Button('cancel', 'Annuler', css_class='btn btn-secondary ms-2',
                       onclick='window.history.back()'),
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        batiment = cleaned_data.get('batiment')
        unite_batie = cleaned_data.get('unite_batie')
        if not batiment and not unite_batie:
            raise forms.ValidationError("Veuillez sélectionner soit un Bâtiment (Campus) soit une Unité Bâtie.")
        return cleaned_data
