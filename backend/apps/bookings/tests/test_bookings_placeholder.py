"""
Tests del motor de reservas — PLACEHOLDER Sprint 0

QA: este módulo es el punto de entrada para los tests de Sprint 1+.

Tests OBLIGATORIOS a implementar (ver docs/SPRINT_0.md y docs/RULES.md):

1. test_create_booking_success
   - Jugador crea reserva -> nace en PENDING_PAYMENT.

2. test_create_booking_in_past_raises_error
   - Intentar reservar un turno pasado -> BookingInPast (HTTP 400).

3. test_create_booking_inactive_court_raises_error
   - Cancha inactiva -> CourtInactive (HTTP 400).

4. test_create_booking_outside_schedule_raises_error
   - Fuera del horario de ScheduleBlock -> OutsideSchedule (HTTP 400).

5. test_overbooking_concurrent_same_slot
   - Dos reservas simultáneas al mismo turno -> solo una gana (SlotAlreadyBooked).
   - CRITICO: usar threading o multiprocessing para simular concurrencia real.

6. test_player_cannot_confirm_booking
   - El rol player no puede llamar a POST /api/bookings/{id}/confirm/ -> 403.

7. test_operator_can_confirm_booking
   - El rol operator puede confirmar -> CONFIRMED + CashMovement generado.

8. test_tenant_isolation_bookings
   - Reserva creada en tenant A no es visible en tenant B (aislamiento multi-tenant).

9. test_booking_xor_user_guest (ADR-008)
   - No se puede tener user Y guest_* simultáneamente.
   - No se puede crear sin ninguno de los dos.

10. test_booking_status_transitions
    - PENDING_PAYMENT -> CONFIRMED -> COMPLETED (happy path).
    - CANCELLED -> cualquier estado está prohibido.
    - COMPLETED -> cualquier estado está prohibido.
"""
