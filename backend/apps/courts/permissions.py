"""
Permisos — app courts

IsTenantAdminOrReadOnly:
  Permite lectura (GET, HEAD, OPTIONS) a cualquier usuario autenticado
  del tenant. Permite escritura (POST, PATCH, DELETE) solo a tenant_admin.

  RBAC.md §4:
    Canchas (Court)    — ABM: solo tenant_admin
    Horarios (ScheduleBlock) — Configurar: solo tenant_admin
    Grilla de disponibilidad — Ver: todos (incluido player)

  La propiedad is_tenant_admin está definida en apps.users.models.User
  y retorna True si role == 'tenant_admin'.

Uso en ViewSets:
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTenantAdminOrReadOnly(BasePermission):
    """
    Permiso de escritura exclusivo para tenant_admin.

    - GET, HEAD, OPTIONS (SAFE_METHODS): cualquier usuario autenticado.
    - POST, PATCH, PUT, DELETE: solo si request.user.is_tenant_admin.

    No aplica a usuarios no autenticados: el DEFAULT_PERMISSION_CLASSES
    global (IsAuthenticated) bloquea el acceso antes de llegar aquí.
    """

    message = "Solo el administrador del complejo puede crear, editar o eliminar canchas y horarios."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_tenant_admin)
