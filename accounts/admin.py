from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ActivityLog


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations UAD', {'fields': ('role', 'telephone', 'photo')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations UAD', {'fields': ('role', 'telephone')}),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'timestamp']
    list_filter = ['action', 'timestamp']
    readonly_fields = ['user', 'action', 'detail', 'ip_address', 'timestamp']
