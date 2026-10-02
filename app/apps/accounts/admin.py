from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ActivityLog, Permission, Role, RolePermissionLink, UserPermissionLink


class RolePermissionInline(admin.TabularInline):
    model = RolePermissionLink
    extra = 1
    autocomplete_fields = ['permission']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'domaine', 'date_creation']
    list_filter = ['domaine']
    search_fields = ['code', 'nom', 'description']
    ordering = ['domaine', 'code']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'is_canonical', 'date_creation']
    list_filter = ['is_canonical']
    search_fields = ['code', 'nom']
    inlines = [RolePermissionInline]


@admin.register(UserPermissionLink)
class UserPermissionLinkAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'is_granted', 'date_creation']
    list_filter = ['is_granted', 'permission__domaine']
    search_fields = ['user__username', 'permission__code', 'permission__nom']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'role', 'assigned_role', 'is_active', 'date_joined']
    list_filter = ['role', 'assigned_role', 'is_active', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'telephone']
    fieldsets = UserAdmin.fieldsets + (
        ('Gouvernance V2 & RBAC', {'fields': ('role', 'assigned_role', 'created_by')}),
        ('Informations complémentaires', {'fields': ('telephone', 'village', 'photo')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Gouvernance V2 & RBAC', {'fields': ('role', 'assigned_role', 'created_by')}),
        ('Informations complémentaires', {'fields': ('telephone', 'village')}),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'timestamp']
    list_filter = ['action', 'timestamp']
    readonly_fields = ['user', 'action', 'detail', 'ip_address', 'timestamp']

