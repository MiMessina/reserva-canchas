"""
Admin de la app users.

Registra el Custom User en el Django Admin del esquema del tenant.

FIX R-08: User hereda de AbstractBaseUser (no AbstractUser), por lo que
UserAdmin debe definir sus propios fieldsets en lugar de extender los de
BaseUserAdmin (que asume username). Se usa ModelAdmin directamente con
las secciones apropiadas para nuestro modelo.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin del Custom User que usa email como identificador (sin username).

    Se redefinen fieldsets y add_fieldsets para eliminar las referencias
    a `username` heredadas de BaseUserAdmin.
    """

    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff", "created_at")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")

    # Reemplaza los fieldsets de BaseUserAdmin (que referencia `username`)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Información personal"), {"fields": ("first_name", "last_name")}),
        (_("Rol y permisos"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Fechas"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    # Formulario de alta de usuario en el admin
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "is_staff", "is_active"),
        }),
    )
