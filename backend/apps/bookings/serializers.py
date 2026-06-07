"""
Serializers — app bookings

Los serializers validan estructura y transforman datos; NO gobiernan negocio (RULES.md §1).
La lógica de negocio (XOR user/guest, concurrencia, transiciones) vive en services.py.

Serializers:
  BookingSerializer       — lectura (lista y detalle).
  BookingCreateSerializer — escritura (crear reserva, invitado o player).
  BookingCancelSerializer — escritura (motivo de cancelación).
  CashMovementSerializer  — lectura de movimientos de caja.
"""

from rest_framework import serializers

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Booking.

    Expone todos los campos públicos de una reserva.
    Usado en GET list, GET detail y como respuesta a mutaciones.
    """

    court_name = serializers.CharField(
        source="court.name",
        read_only=True,
        help_text="Nombre de la cancha.",
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
        help_text="Etiqueta legible del estado de la reserva.",
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "court",
            "court_name",
            "user",
            "guest_name",
            "guest_phone",
            "start_dt",
            "end_dt",
            "status",
            "status_display",
            "price",
            "cancellation_reason",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "court_name",
            "status_display",
            "end_dt",
            "price",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]


class BookingCreateSerializer(serializers.Serializer):
    """
    Serializer de escritura para crear una reserva.

    Valida solo estructura. La lógica de negocio (XOR, overbooking, pasado,
    schedule) vive en bookings/services.py::create_booking().

    Campos:
      court      — PK de la cancha activa.
      start_dt   — datetime ISO 8601 timezone-aware. El backend trabaja en UTC.
      guest_name — nombre del invitado (requerido si no hay JWT).
      guest_phone— teléfono del invitado (requerido si no hay JWT).

    La validación XOR se hace en services.py, no aquí, para mantener
    la regla de que los serializers no gobiernan negocio.
    """

    court = serializers.PrimaryKeyRelatedField(
        queryset=Court.objects.filter(is_active=True),
        help_text="PK de la cancha activa a reservar.",
    )
    start_dt = serializers.DateTimeField(
        help_text="Fecha y hora de inicio en UTC (ISO 8601 timezone-aware).",
    )
    guest_name = serializers.CharField(
        max_length=120,
        required=False,
        default="",
        allow_blank=True,
        help_text="Nombre del invitado. Obligatorio si no hay usuario autenticado (ADR-008).",
    )
    guest_phone = serializers.CharField(
        max_length=30,
        required=False,
        default="",
        allow_blank=True,
        help_text="Teléfono del invitado. Obligatorio si no hay usuario autenticado (ADR-008).",
    )


class BookingCancelSerializer(serializers.Serializer):
    """
    Serializer de escritura para cancelar una reserva.

    El campo reason es opcional; si no se provee, el service usa un valor por defecto.
    """

    reason = serializers.CharField(
        max_length=255,
        required=False,
        default="",
        allow_blank=True,
        help_text="Motivo de cancelación (opcional).",
    )


class CashMovementSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para CashMovement.

    Expone todos los campos del movimiento de caja más campos derivados
    para facilitar la presentación en el panel de caja del cajero.
    """

    booking_court = serializers.CharField(
        source="booking.court.name",
        read_only=True,
        help_text="Nombre de la cancha de la reserva.",
    )
    operator_email = serializers.CharField(
        source="operator.email",
        read_only=True,
        help_text="Email del operador que registró el movimiento.",
    )

    class Meta:
        model = CashMovement
        fields = [
            "id",
            "booking",
            "booking_court",
            "operator",
            "operator_email",
            "amount",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "booking_court",
            "operator_email",
            "created_at",
        ]
