"""
Modelos — app bookings

Entidades del motor de reservas: Booking y CashMovement.

ADR-006: Detección de overbooking por solapamiento de intervalos [start_dt, end_dt).
         end_dt = start_dt + court.slot_duration_minutes (calculado en services.py).
ADR-008: Jugador registrado (user) XOR invitado (guest_name + guest_phone).
         La regla XOR se valida en bookings/services.py, no aquí.
ADR-011: Booking hereda de TimeStampedSoftDeleteModel (is_active, created_at, updated_at).
         CashMovement NO hereda de TimeStampedSoftDeleteModel: es inmutable, solo se crea.

Reglas de datos (RULES.md §4, DER.md):
  - Soft-delete obligatorio en Booking via is_active (heredado). Prohibido DELETE físico.
  - CashMovement es inmutable: nunca se modifica ni se da de baja lógica.
  - Fechas/horas en UTC (USE_TZ=True en settings).
  - Toda reserva nace en PENDING_PAYMENT (WORKFLOW.md §3).
  - price es un snapshot de court.base_price en el momento de la reserva.
"""

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedSoftDeleteModel


class Booking(TimeStampedSoftDeleteModel):
    """
    Reserva de una cancha por un usuario o invitado.

    Ciclo de vida (WORKFLOW.md §3-4):
      PENDING_PAYMENT → CONFIRMED → COMPLETED
                     → CANCELLED
                   (CONFIRMED puede cancelarse también)

    Regla XOR (ADR-008):
      - user no None: guest_name y guest_phone deben estar vacíos.
      - user es None: guest_name y guest_phone son obligatorios (no vacíos).
      La validación vive en bookings/services.py.

    Campos de intervalo (ADR-006):
      start_dt y end_dt en UTC. end_dt = start_dt + court.slot_duration_minutes.
      El overbooking se detecta por solapamiento de estos intervalos.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pendiente de pago"
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"
        COMPLETED = "COMPLETED", "Completada"

    court = models.ForeignKey(
        "courts.Court",
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Cancha",
        help_text="Cancha reservada.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name="Usuario",
        help_text="Usuario registrado que reserva. Null si es reserva de invitado (ADR-008).",
    )
    guest_name = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Nombre del invitado",
        help_text="Nombre del jugador invitado (cuando user es null, ADR-008).",
    )
    guest_phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Teléfono del invitado",
        help_text="Teléfono de contacto del invitado (cuando user es null, ADR-008).",
    )
    start_dt = models.DateTimeField(
        verbose_name="Inicio del turno (UTC)",
        help_text="Fecha y hora de inicio del turno, siempre en UTC.",
    )
    end_dt = models.DateTimeField(
        verbose_name="Fin del turno (UTC)",
        help_text="Fecha y hora de fin. end_dt = start_dt + court.slot_duration_minutes (ADR-006).",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        verbose_name="Estado",
        help_text="Estado de la reserva según el workflow definido en WORKFLOW.md.",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio",
        help_text="Snapshot del precio de la cancha al momento de crear la reserva.",
    )
    cancellation_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Motivo de cancelación",
        help_text="Motivo de cancelación. Obligatorio si el estado es CANCELLED.",
    )

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-start_dt"]
        indexes = [
            # Índice compuesto para la consulta de overbooking (solapamiento de intervalos)
            models.Index(fields=["court", "status", "start_dt", "end_dt"], name="booking_overlap_idx"),
        ]

    def __str__(self):
        identifier = self.user.email if self.user else self.guest_name
        return f"Reserva #{self.pk} — {self.court.name} — {identifier} — {self.start_dt:%Y-%m-%d %H:%M} UTC"


class CashMovement(models.Model):
    """
    Movimiento de caja generado al confirmar una reserva.

    Registro INMUTABLE: solo se crea en confirm_booking(), nunca se modifica
    ni se da de baja lógica. No hereda de TimeStampedSoftDeleteModel a propósito.

    Una reserva puede tener múltiples movimientos si se vuelve a confirmar
    (tras cancelación de una confirmada, la nota de cancelación queda en el campo notes).
    La integridad la garantiza el service layer.
    """

    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="cash_movements",
        verbose_name="Reserva",
        help_text="Reserva a la que corresponde este movimiento de caja.",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cash_movements",
        verbose_name="Operador",
        help_text="Usuario (operator o admin) que registró el movimiento.",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto",
        help_text="Monto del movimiento en pesos. Corresponde al precio de la reserva.",
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Notas",
        help_text="Notas adicionales (ej: referencia de transferencia, motivo de cancelación).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
        help_text="Timestamp de creación en UTC. Inmutable.",
    )

    class Meta:
        verbose_name = "Movimiento de caja"
        verbose_name_plural = "Movimientos de caja"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CashMovement #{self.pk} — Reserva #{self.booking_id} — ${self.amount}"
