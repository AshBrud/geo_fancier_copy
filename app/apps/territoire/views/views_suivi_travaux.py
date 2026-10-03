from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import domaine_required
from territoire.models import SuiviTravaux
from territoire.forms import SuiviTravauxForm


@login_required
@domaine_required
def suivi_travaux_list(request):
    suivis = SuiviTravaux.objects.select_related(
        'construction', 'maitre_ouvrage'
    ).order_by('-date_creation')
    return render(request, 'territoire/suivi_travaux_list.html', {'suivis': suivis})


@login_required
@domaine_required
def suivi_travaux_update(request, pk):
    suivi = get_object_or_404(SuiviTravaux, pk=pk)
    form = SuiviTravauxForm(request.POST or None, instance=suivi)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Suivi des travaux « {suivi.construction.nom_projet} » mis à jour.')
        return redirect('territoire:suivi_travaux')
    return render(request, 'territoire/suivi_travaux_form.html', {
        'form': form, 'suivi': suivi,
    })
