"""
Service layer — Motor de Reservas (bookings/services.py)

Sprint 0: PLACEHOLDER. El motor de reservas se implementa en Sprint 1+.

IMPORTANTE: este es el archivo más crítico del sistema.
Toda la lógica del motor de reservas vive AQUÍ y solo aquí (RULES.md).

Reglas inviolables del motor (ver docs/WORKFLOW.md y docs/RULES.md):

1. CONCURRENCIA: toda reserva usa select_for_update() dentro de
   transaction.atomic(). Sin excepción (ADR-003).

2. ESTADO INICIAL: la reserva nace siempre en PENDING_PAYMENT.

3. OVERBOOKING: se detecta por solapamiento de intervalos [start_dt, end_dt),
   NO por igualdad exacta de start_dt (ADR-006).

4. PASADO: no se permite reservar en el pasado.

5. XOR INVITADO/CUENTA: una reserva tiene user XOR guest_* (ADR-008).

6. SOFT-DELETE: prohibido DELETE físico.

7. AUDITORÍA: toda creación/transición genera evento auditable.

Estructura esperada en Sprint 1+:

    class BookingInPast(Exception): ...
    class SlotAlreadyBooked(Exception): ...
    class CourtInactive(Exception): ...
    class OutsideSchedule(Exception): ...
    class InvalidTransition(Exception): ...

    def create_booking(*, court, start_dt, user=None, guest_name=None, guest_phone=None) -> Booking:
        # 1. Validar cancha activa
        # 2. No reservar en el pasado
        # 3. Validar horario dentro de ScheduleBlock
        # 4. Validar XOR user/guest (ADR-008)
        # 5. Calcular end_dt = start_dt + court.slot_duration_minutes
        # with transaction.atomic():
        #   6. select_for_update() sobre la cancha
        #   7. Detectar overbooking por solapamiento [start_dt, end_dt)
        #   8. Crear Booking en PENDING_PAYMENT
        #   9. audit("booking.created", ...)
        #   10. return booking

    def confirm_booking(*, booking, confirmed_by) -> Booking:
        # Transición PENDING_PAYMENT -> CONFIRMED
        # Genera CashMovement

    def cancel_booking(*, booking, cancelled_by, reason: str) -> Booking:
        # Transición PENDING_PAYMENT|CONFIRMED -> CANCELLED

    def complete_booking(*, booking, completed_by) -> Booking:
        # Transición CONFIRMED -> COMPLETED (solo después del end_dt)
"""
