from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.forms import ProfileForm


@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile/profile.html', {'form': form})
