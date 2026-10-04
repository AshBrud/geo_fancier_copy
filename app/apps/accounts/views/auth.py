from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import ActivityLog
from accounts.forms import LoginForm, RegisterForm

User = get_user_model()


def _suivant(request):
    """URL de retour (?next=) si elle pointe bien vers la plateforme."""
    nxt = request.POST.get('next') or request.GET.get('next') or ''
    if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                       require_https=request.is_secure()):
        return nxt
    return ''


def _contexte_commune():
    """Identité du territoire et zones affichées dans le défilement des pages d'accès."""
    from dossiers.models import Dossier, ZoneSecteur
    return {
        'commune': Dossier.objects.first(),
        'villages_defilement': ZoneSecteur.objects.order_by('nom').only('nom', 'code'),
    }


def login_view(request):
    # Pas de redirection automatique quand une session est déjà ouverte : sur un
    # ordinateur partagé, chacun doit pouvoir se connecter avec son propre compte
    # (la nouvelle connexion remplace alors la session précédente).
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.POST.get('ajax') == '1'

    if request.method == 'POST':
        action = request.POST.get('action', 'login')

        # Étape 2 : Définition obligatoire du nouveau mot de passe
        if action == 'set_new_password':
            user_id = request.session.get('force_change_user_id')
            if not user_id:
                msg = "Votre session a expiré. Veuillez vous reconnecter."
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': msg}, status=400)
                messages.error(request, msg)
                return redirect('accounts:login')

            target_user = User.objects.filter(pk=user_id, is_active=True).first()
            if not target_user:
                request.session.pop('force_change_user_id', None)
                msg = "Compte introuvable ou inactif."
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': msg}, status=400)
                messages.error(request, msg)
                return redirect('accounts:login')

            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()

            if len(new_password) < 6:
                err = "Le nouveau mot de passe doit comporter au moins 6 caractères."
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': err}, status=400)
                messages.error(request, err)
                return redirect('accounts:login')

            if new_password != confirm_password:
                err = "Les deux mots de passe ne correspondent pas."
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': err}, status=400)
                messages.error(request, err)
                return redirect('accounts:login')

            if target_user.check_password(new_password):
                err = "Le nouveau mot de passe doit être différent du mot de passe temporaire initial."
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': err}, status=400)
                messages.error(request, err)
                return redirect('accounts:login')

            # Application du nouveau mot de passe et levée du drapeau
            target_user.set_password(new_password)
            target_user.must_change_password = False
            target_user.save(update_fields=['password', 'must_change_password'])

            request.session.pop('force_change_user_id', None)

            # Connexion formelle
            login(request, target_user)
            ActivityLog.objects.create(
                user=target_user,
                action='PREMIER_CHANGEMENT_MDP',
                detail="Définition obligatoire du mot de passe personnel à la première connexion.",
                ip_address=request.META.get('REMOTE_ADDR')
            )

            redirect_url = _suivant(request) or reverse('dossiers:list')
            if is_ajax:
                return JsonResponse({'ok': True, 'redirect_url': redirect_url})
            return redirect(redirect_url)

        # Étape 1 : Vérification des identifiants
        form = LoginForm(request, data=request.POST or None)
        if form.is_valid():
            user = form.get_user()

            # Vérification si le changement de mot de passe est obligatoire
            if getattr(user, 'must_change_password', False):
                request.session['force_change_user_id'] = user.pk
                if is_ajax:
                    return JsonResponse({
                        'ok': True,
                        'must_change_password': True,
                        'user_display': user.get_full_name() or user.username,
                        'role_display': user.get_role_display(),
                    })
                return render(request, 'accounts/auth/login.html', {
                    'form': form,
                    'force_change_step': True,
                    'force_user': user,
                    'page_auth': True,
                    **_contexte_commune(),
                })

            precedent = request.user if request.user.is_authenticated else None
            if precedent and precedent.pk != user.pk:
                ActivityLog.objects.create(
                    user=precedent, action='Déconnexion (changement de compte)',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            login(request, user)
            ActivityLog.objects.create(
                user=user, action='Connexion',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            redirect_url = _suivant(request) or reverse('dossiers:list')
            if is_ajax:
                return JsonResponse({'ok': True, 'redirect_url': redirect_url})
            return redirect(redirect_url)
        else:
            if is_ajax:
                error_msg = 'Identifiant ou mot de passe incorrect.'
                if form.non_field_errors():
                    error_msg = form.non_field_errors()[0]
                elif form.errors:
                    first_field = next(iter(form.errors))
                    error_msg = form.errors[first_field][0]
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)

    else:
        form = LoginForm(request)

    from dossiers.models import ZoneSecteur, UniteBatie
    from drones.models import Orthophoto
    return render(request, 'accounts/auth/login.html', {
        'form': form,
        'nb_espaces': ZoneSecteur.objects.count(),
        'nb_batiments': UniteBatie.objects.count(),
        'nb_orthophotos': Orthophoto.objects.count(),
        'next': _suivant(request),
        'page_auth': True,
        'force_user': None,
        'force_change_step': False,
        **_contexte_commune(),
    })


def register_view(request):
    """
    L'inscription publique autonome est formellement fermée dans GéoFoncier.
    Les comptes sont créés par mandat institutionnel par le Superuser ou un Admin habilité.
    """
    messages.info(request, "L'auto-inscription est fermée. Veuillez contacter un administrateur pour l'attribution d'un compte.")
    return redirect('accounts:login')


@login_required
def logout_view(request):
    if request.method == 'POST':
        ActivityLog.objects.create(
            user=request.user, action='Déconnexion',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        logout(request)
        return redirect('accounts:login')
    return redirect('dashboard:index')
