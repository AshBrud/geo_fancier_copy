from django.urls import path
from django.contrib.auth import views as auth_views
from accounts.views import auth, profile, management

app_name = 'accounts'

urlpatterns = [
    # =========================================================================
    # 1. AUTHENTIFICATION (accounts/views/auth.py)
    # =========================================================================
    path('login/', auth.login_view, name='login'),
    path('register/', auth.register_view, name='register'),
    path('logout/', auth.logout_view, name='logout'),

    # =========================================================================
    # 2. PROFIL UTILISATEUR (accounts/views/profile.py)
    # =========================================================================
    path('profile/', profile.profile_view, name='profile'),

    # =========================================================================
    # 3. GESTION DES UTILISATEURS & AUDIT (accounts/views/management.py)
    # =========================================================================
    path('users/', management.users_list, name='users'),
    path('users/create/', management.user_create, name='user_create'),
    path('users/<int:pk>/update/', management.user_update, name='user_update'),
    path('users/<int:pk>/delete/', management.user_delete, name='user_delete'),
    path('users/<int:pk>/activate/', management.user_activate, name='user_activate'),
    path('roles/matrix/', management.roles_matrix_manage, name='roles_matrix_manage'),
    path('activity/', management.activity_log, name='activity_log'),

    # =========================================================================
    # 4. RÉINITIALISATION DU MOT DE PASSE (password_reset/)
    # =========================================================================
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset/request.html',
             email_template_name='accounts/password_reset/email_body.html',
             subject_template_name='accounts/password_reset/email_subject.txt',
             success_url='/accounts/password-reset/done/',
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset/done.html',
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset/confirm.html',
             success_url='/accounts/password-reset/complete/',
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset/complete.html',
         ),
         name='password_reset_complete'),
]
