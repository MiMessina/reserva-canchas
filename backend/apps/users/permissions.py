"""
Permisos base (RBAC) — app users

Clases de permiso reutilizables para los endpoints de DRF.
Se usan como permission_classes en las views de cada dominio.

Reglas (RBAC.md):
  - Todo endpoint requiere JWT + tenant (salvo healthcheck y grilla pública).
  - El tenant lo resuelve el middleware de django-tenants; no hay que validarlo
    manualmente en el permiso (ya corre en el esquema correcto).
  - Los permisos aquí validan el ROL dentro del tenant activo.

Sprint 0: permisos base definidos. Se expanden con los endpoints de Sprint 1+.
"""

from rest_framework.permissions import BasePermission


class IsTenantAdmin(BasePermission):
    """
    Permite acceso solo a usuarios con role=tenant_admin.
    Usado para: ABM de canchas, horarios, configuración del complejo.
    """

    message = "Se requiere el rol de administrador del complejo."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "tenant_admin"
        )


class IsOperatorOrAdmin(BasePermission):
    """
    Permite acceso a operator y tenant_admin.
    Usado para: confirmar reservas, registrar señas, ver caja.
    """

    message = "Se requiere el rol de cajero o administrador del complejo."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("tenant_admin", "operator")
        )


class IsStaffOfComplex(BasePermission):
    """
    Alias semántico para IsOperatorOrAdmin.
    Staff = tenant_admin | operator (personas internas del complejo).
    """

    message = "Solo el personal del complejo puede realizar esta acción."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("tenant_admin", "operator")
        )


class IsPlayer(BasePermission):
    """
    Permite acceso solo a usuarios con role=player.
    Los endpoints de player generalmente usan AllowAny o IsAuthenticated;
    este permiso sirve cuando se quiere restringir a solo jugadores.
    """

    message = "Solo los jugadores pueden realizar esta acción."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "player"
        )


class IsOwnerOrStaff(BasePermission):
    """
    Object-level: el jugador puede ver/cancelar SOLO sus propias reservas.
    El staff (operator/tenant_admin) puede ver/gestionar cualquier reserva.

    Uso:
        permission_classes = [IsAuthenticated, IsOwnerOrStaff]
        def has_object_permission(self, request, view, obj):
            ...

    Sprint 0: definido. Se usa en el endpoint de detalle de Booking (Sprint 1+).
    """

    message = "Solo podés gestionar tus propias reservas."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # Staff puede todo
        if request.user.role in ("tenant_admin", "operator"):
            return True
        # El jugador solo accede a sus propios recursos
        # obj puede ser Booking (con user FK o guest)
        return getattr(obj, "user_id", None) == request.user.pk
