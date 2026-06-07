"""
Service layer — app bookings

Toda la lógica de negocio de reservas y caja vive aquí (RULES.md §4, ARCHITECTURE.md §4).
Prohibido duplicar en views ni serializers.

Funciones exportadas:
  create_booking(*, court_id, start_dt, user=None, guest_name='', guest_phone='') -> Booking
  confirm_booking(*, booking, operator) -> Booking
  cancel_booking(*, booking, cancelled_by, reason='') -> Booking
  complete_booking(*, booking) -> Booking

Validaciones de negocio (lanzadas como DRF ValidationError con código de negocio):
  BOOKING_IN_PAST     — start_dt <= now()
  COURT_INACTIVE      — cancha inactiva o inexistente
  OUTSIDE_SCHEDULE    — slot fuera de ScheduleBlock activo
  SLOT_ALREADY_BOOKED — solapamiento de intervalos con reserva existente (overbooking)
  USER_XOR_GUEST      — debe tener user O guest_name+guest_phone, no ambos ni ninguno
  INVALID_TRANSITION  — transición de estado no permitida por el workflow

Regla CRÍTICA (ADR-003, RULES.md §4):
  create_booking usa select_for_update() dentro de transaction.atomic() para
  garantizar ausencia de overbooking bajo concurrencia.

Regla de solapamiento (ADR-006):
  Overbooking se detecta cuando:
    existente.start_dt < nuevo.end_dt  AND  existente.end_dt > nuevo.start_dt
  Cubre parcial izquierdo, parcial derecho, contenido y contenedor.
  Solo se consideran reservas activas en PENDING_PAYMENT o CONFIRMED.

Regla XOR de identidad (ADR-008):
  user no None → guest_name y guest_phone deben estar vacíos.
  user es None → guest_name y guest_phone son obligatorios.

Zona horaria (RULES.md §4):
  start_dt y end_dt se guardan en UTC.
  La validación de ScheduleBlock convierte a America/Argentina/Buenos_Aires
  para comparar con open_time/close_time (que son horas locales del complejo).

Códigos de negocio (API_GUIDELINES.md §7):
  SLOT_ALREADY_BOOKED, BOOKING_IN_PAST, COURT_INACTIVE, OUTSIDE_SCHEDULE,
  INVALID_TRANSITION, USER_XOR_GUEST
"""

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court, ScheduleBlock

logger = logging.getLogger(__name__)

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _build_error(code: str, message: str, details: dict | None = None) -> dict:
    """Construye el payload de error estándar (API_GUIDELINES.md §7)."""
    payload: dict = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return {"error": payload}


def _validate_identity(user, guest_name: str, guest_phone: str) -> None:
    """
    Valida la regla XOR de identidad (ADR-008).

    user no None → guest_name y guest_phone deben estar vacíos.
    user es None → guest_name y guest_phone son obligatorios.
    """
    if user is not None and (guest_name.strip() or guest_phone.strip()):
        raise ValidationError(
            _build_error(
                "USER_XOR_GUEST",
                "Si el usuario está autenticado no se deben enviar guest_name ni guest_phone.",
            )
        )
    if user is None and not (guest_name.strip() and guest_phone.strip()):
        raise ValidationError(
            _build_error(
                "USER_XOR_GUEST",
                "Las reservas de invitado requieren guest_name y guest_phone.",
            )
        )


def _validate_schedule(court: Court, start_dt, end_dt) -> None:
    """
    Valida que el slot [start_dt, end_dt) caiga completamente dentro
    de un ScheduleBlock activo de la cancha.

    La comparación se realiza en hora Buenos Aires porque open_time/close_time
    son horas locales del complejo (no UTC).
    """
    start_ba = start_dt.astimezone(BUENOS_AIRES)
    end_ba = end_dt.astimezone(BUENOS_AIRES)
    weekday = start_ba.weekday()
    start_time = start_ba.time()
    end_time = end_ba.time()

    block_ok = ScheduleBlock.objects.filter(
        court=court,
        weekday=weekday,
        is_active=True,
        open_time__lte=start_time,
        close_time__gte=end_time,
    ).exists()

    if not block_ok:
        raise ValidationError(
            _build_error(
                "OUTSIDE_SCHEDULE",
                "El horario solicitado está fuera del horario de disponibilidad de la cancha.",
                {
                    "court": court.pk,
                    "start_dt": start_dt.isoformat(),
                    "end_dt": end_dt.isoformat(),
                    "weekday": weekday,
                    "start_time_ba": start_time.strftime("%H:%M"),
                    "end_time_ba": end_time.strftime("%H:%M"),
                },
            )
        )


# ---------------------------------------------------------------------------
# create_booking
# ---------------------------------------------------------------------------

def create_booking(
    *,
    court_id: int,
    start_dt,
    user=None,
    guest_name: str = "",
    guest_phone: str = "",
) -> Booking:
    """
    Crea una reserva nueva en estado PENDING_PAYMENT.

    CRÍTICO: usa select_for_update() dentro de transaction.atomic() para
    garantizar ausencia de overbooking bajo concurrencia (ADR-003, RULES.md §4).

    Parámetros:
      court_id    — PK de la cancha a reservar.
      start_dt    — datetime timezone-aware en UTC.
      user        — instancia User autenticado, o None para reserva de invitado.
      guest_name  — nombre del invitado (obligatorio si user es None).
      guest_phone — teléfono del invitado (obligatorio si user es None).

    Validaciones (en orden):
      1. No en el pasado.
      2. Identidad XOR (ADR-008).
      3. Cancha activa (con bloqueo pesimista).
      4. Slot dentro de ScheduleBlock activo.
      5. Sin overbooking (solapamiento de intervalos).

    Retorna la instancia Booking creada.
    """
    # Validación 1: no en el pasado (fail-fast fuera de la transacción)
    if start_dt <= timezone.now():
        raise ValidationError(
            _build_error(
                "BOOKING_IN_PAST",
                "No se puede reservar un turno en el pasado.",
                {"start_dt": start_dt.isoformat()},
            )
        )

    # Validación 2: identidad XOR (ADR-008)
    _validate_identity(user, guest_name, guest_phone)

    with transaction.atomic():
        # Validación 3: cancha activa con bloqueo pesimista (ADR-003)
        # El select_for_update() sobre la fila de la cancha serializa accesos
        # concurrentes al mismo turno.
        try:
            court = Court.objects.select_for_update().get(pk=court_id, is_active=True)
        except Court.DoesNotExist:
            raise ValidationError(
                _build_error(
                    "COURT_INACTIVE",
                    "La cancha no existe o no está disponible.",
                    {"court_id": court_id},
                )
            )

        end_dt = start_dt + timedelta(minutes=court.slot_duration_minutes)

        # Validación 4: dentro de ScheduleBlock activo
        _validate_schedule(court, start_dt, end_dt)

        # Validación 5: no overbooking — solapamiento de intervalos (ADR-006)
        # Condición: existente.start_dt < end_dt AND existente.end_dt > start_dt
        overlap_exists = Booking.objects.filter(
            court=court,
            is_active=True,
            status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED],
            start_dt__lt=end_dt,
            end_dt__gt=start_dt,
        ).exists()

        if overlap_exists:
            raise ValidationError(
                _build_error(
                    "SLOT_ALREADY_BOOKED",
                    "Ese turno ya fue reservado. Elegí otro horario.",
                    {
                        "court": court_id,
                        "start_dt": start_dt.isoformat(),
                        "end_dt": end_dt.isoformat(),
                    },
                )
            )

        booking = Booking.objects.create(
            court=court,
            user=user,
            guest_name=guest_name,
            guest_phone=guest_phone,
            start_dt=start_dt,
            end_dt=end_dt,
            price=court.base_price,
            status=Booking.Status.PENDING_PAYMENT,
        )

        logger.info(
            "Reserva creada: id=%s court=%s start=%s status=%s",
            booking.pk,
            court_id,
            start_dt.isoformat(),
            booking.status,
        )
        return booking


# ---------------------------------------------------------------------------
# confirm_booking
# ---------------------------------------------------------------------------

def confirm_booking(*, booking: Booking, operator) -> Booking:
    """
    Transición: PENDING_PAYMENT → CONFIRMED.

    Genera un CashMovement con el precio de la reserva.
    Solo puede ejecutarla un operator o tenant_admin (verificado en la view/permiso).

    Lanza ValidationError con INVALID_TRANSITION si la reserva no está en PENDING_PAYMENT.

    Parámetros:
      booking  — instancia Booking a confirmar.
      operator — instancia User (operator o admin) que confirma.

    Retorna la instancia Booking actualizada.
    """
    if booking.status != Booking.Status.PENDING_PAYMENT:
        raise ValidationError(
            _build_error(
                "INVALID_TRANSITION",
                (
                    f"No se puede confirmar una reserva en estado '{booking.get_status_display()}'. "
                    "Solo se pueden confirmar reservas en estado PENDING_PAYMENT."
                ),
                {
                    "current_status": booking.status,
                    "required_status": Booking.Status.PENDING_PAYMENT,
                },
            )
        )

    with transaction.atomic():
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])

        CashMovement.objects.create(
            booking=booking,
            operator=operator,
            amount=booking.price,
            notes="Seña confirmada por operador.",
        )

    logger.info(
        "Reserva confirmada: id=%s operator=%s amount=%s",
        booking.pk,
        operator.pk,
        booking.price,
    )
    return booking


# ---------------------------------------------------------------------------
# cancel_booking
# ---------------------------------------------------------------------------

def cancel_booking(*, booking: Booking, cancelled_by, reason: str = "") -> Booking:
    """
    Transición: PENDING_PAYMENT o CONFIRMED → CANCELLED.

    Reglas:
      - No se puede cancelar una reserva ya CANCELLED o COMPLETED.
      - Si estaba CONFIRMED, se registra un CashMovement con monto negativo
        para reflejar la devolución en la caja del día (el movimiento original
        es inmutable y no se toca).
      - cancelled_by puede ser None (cancelación sin usuario autenticado).

    Parámetros:
      booking       — instancia Booking a cancelar.
      cancelled_by  — instancia User que cancela, o None.
      reason        — motivo de cancelación (opcional).

    Retorna la instancia Booking actualizada.
    """
    if booking.status in (Booking.Status.CANCELLED, Booking.Status.COMPLETED):
        raise ValidationError(
            _build_error(
                "INVALID_TRANSITION",
                f"No se puede cancelar una reserva en estado '{booking.get_status_display()}'.",
                {"current_status": booking.status},
            )
        )

    was_confirmed = booking.status == Booking.Status.CONFIRMED

    with transaction.atomic():
        booking.status = Booking.Status.CANCELLED
        booking.cancellation_reason = reason if reason.strip() else "Sin motivo especificado."
        booking.save(update_fields=["status", "cancellation_reason", "updated_at"])

        # Si estaba confirmada, registrar contrapartida en caja (monto negativo)
        if was_confirmed and cancelled_by is not None:
            actor_label = cancelled_by.email if cancelled_by else "sistema"
            CashMovement.objects.create(
                booking=booking,
                operator=cancelled_by,
                amount=-booking.price,
                notes=(
                    f"Cancelación de reserva confirmada. "
                    f"Motivo: {booking.cancellation_reason}. "
                    f"Actor: {actor_label}."
                ),
            )

    logger.info(
        "Reserva cancelada: id=%s cancelled_by=%s reason=%s",
        booking.pk,
        cancelled_by.pk if cancelled_by else "anonimo",
        reason,
    )
    return booking


# ---------------------------------------------------------------------------
# complete_booking
# ---------------------------------------------------------------------------

def complete_booking(*, booking: Booking) -> Booking:
    """
    Transición: CONFIRMED → COMPLETED.

    Solo se puede completar una reserva CONFIRMED cuyo end_dt ya haya pasado.

    Lanza ValidationError con INVALID_TRANSITION si:
      - La reserva no está en CONFIRMED.
      - end_dt > timezone.now() (el turno aún no terminó).

    Parámetros:
      booking — instancia Booking a completar.

    Retorna la instancia Booking actualizada.
    """
    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError(
            _build_error(
                "INVALID_TRANSITION",
                (
                    f"No se puede completar una reserva en estado '{booking.get_status_display()}'. "
                    "Solo se pueden completar reservas en estado CONFIRMED."
                ),
                {
                    "current_status": booking.status,
                    "required_status": Booking.Status.CONFIRMED,
                },
            )
        )

    if booking.end_dt > timezone.now():
        raise ValidationError(
            _build_error(
                "INVALID_TRANSITION",
                "No se puede completar un turno que aún no terminó.",
                {
                    "end_dt": booking.end_dt.isoformat(),
                    "now": timezone.now().isoformat(),
                },
            )
        )

    booking.status = Booking.Status.COMPLETED
    booking.save(update_fields=["status", "updated_at"])

    logger.info("Reserva completada: id=%s", booking.pk)
    return booking
