from django import forms
from territoire.models import SuiviTravaux


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
