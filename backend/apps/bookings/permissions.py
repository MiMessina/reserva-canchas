"""
Permisos — app bookings

Implementa los permisos del módulo de reservas (RBAC.md §4):

  IsOperatorOrAdmin:
    Permite acceso solo a operator o tenant_admin.
    Usado en: confirm, complete, cancel (staff), list de cash-movements.

  IsBookingOwnerOrStaff:
    Permite acceso al propio jugador (booking.user == request.user)
    o a cualquier staff del complejo (operator o admin).
    Usado en: retrieve de booking, cancel propio.

Nota: la action 'create' usa AllowAny directamente en el ViewSet,
ya que la reserva de invitados no requiere JWT (ADR-008).

La validación de "solo puede cancelar su propia reserva" se hace
en la view comparando booking.user == request.user antes de llamar
al service. El permiso grueso (autenticado o no) se controla aquí.
"""

from rest_framework.permissions import BasePermission


class IsOperatorOrAdmin(BasePermission):
    """
    Permite acceso solo a operator o tenant_admin.

    Ambos roles forman el "staff del complejo" (User.is_staff_of_complex).
    El acceso se deniega a players y a usuarios no autenticados.
    """

    message = "Solo el operador o administrador del complejo puede ejecutar esta acción."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff_of_complex
        )
