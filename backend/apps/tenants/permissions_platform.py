"""
Permisos para el Panel de System Admin (ADR-013).

El system_admin es el superuser de Django (django.contrib.auth.User),
que vive en el esquema `public`. Es completamente diferente al Custom User
de TENANT_APPS (apps.users.User).

Aislamiento de JWT (ADR-013 §Positivas):
  - El JWT de system_admin se emite contra auth.User (PUBLIC_SCHEMA_URLCONF).
  - El JWT de tenant users se emite contra apps.users.User (ROOT_URLCONF).
  - Dado que usan modelos distintos en esquemas distintos, un token de uno
    NO autentica al otro: el backend lo rechazará en la consulta al modelo.

Uso:
  permission_classes = [IsSystemAdmin]
"""

from rest_framework.permissions import BasePermission


class IsSystemAdmin(BasePermission):
    """
    Permite acceso solo a django.contrib.auth.User con is_superuser=True.

    Este permiso se usa exclusivamente en los endpoints de /api/platform/
    que corren bajo PUBLIC_SCHEMA_URLCONF (esquema public).

    No confundir con apps.users.User (Custom User de TENANT_APPS):
    el system_admin es el superuser Django del esquema public.
    """

    message = "Solo el administrador de plataforma puede realizar esta acción."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
