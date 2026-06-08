"""
Serializers — app bookings

Los serializers validan estructura y transforman datos; NO gobiernan negocio (RULES.md §1).
La lógica de negocio (XOR user/guest, concurrencia, transiciones) vive en services.py.

Serializers:
  BookingPublicSerializer      — respuesta pública (create, player). Sin datos de contacto de terceros.
  BookingStaffSerializer       — respuesta staff (list, retrieve staff, confirm, complete). Con contacto.
  BookingSerializer            — alias de BookingStaffSerializer para compatibilidad interna.
  BookingCreateSerializer      — escritura (crear reserva, invitado o player).
  BookingCancelSerializer      — escritura (motivo de cancelación).
  CashMovementSerializer       — lectura de movimientos de caja.
  CashDailySummarySerializer   — lectura del resumen diario de caja (summary endpoint).
  BookingsTodaySummarySerializer — lectura de conteos de reservas de hoy por estado (dashboard).
  DashboardSerializer          — lectura del resumen del día para el panel de inicio (dashboard).
"""

from rest_framework import serializers

from apps.bookings.models import Booking, CashMovement
from apps.courts.models import Court


class BookingPublicSerializer(serializers.ModelSerializer):
    """
    Respuesta pública para el creador de la reserva y para players.

    No expone guest_phone, guest_name ni la FK user para proteger
    datos personales de terceros (Fix de seguridad Sprint 2).
    Usado en: POST /api/bookings/ (create) y retrieve de players.
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
            "start_dt",
            "end_dt",
            "status",
            "status_display",
            "price",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BookingStaffSerializer(serializers.ModelSerializer):
    """
    Respuesta para operator y tenant_admin.

    Incluye datos de contacto del jugador/invitado (guest_name, guest_phone, user).
    Usado en: GET list, confirm, complete, cancel (staff), retrieve (staff).
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
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
        allow_null=True,
        help_text="Email del usuario registrado. Null si es reserva de invitado.",
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "court",
            "court_name",
            "user",
            "user_email",
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
        read_only_fields = fields


# Alias para compatibilidad con código existente que importa BookingSerializer.
# Apunta al serializer completo (staff). Las views nuevas usan los nombres explícitos.
BookingSerializer = BookingStaffSerializer


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


class CashDailySummarySerializer(serializers.Serializer):
    """
    Serializer de lectura para el resumen diario de caja.

    Devuelve los totales calculados por get_daily_cash_summary() en selectors.py.
    Solo valida estructura; el cálculo vive en el selector (RULES.md §1).

    Campos:
      date              — fecha del resumen (YYYY-MM-DD, hora Buenos Aires).
      total             — neto del día (ingresos + devoluciones).
      ingresos          — suma de señas/pagos confirmados (amount > 0).
      devoluciones      — suma de devoluciones por cancelación (amount < 0, negativo).
      movements_count   — cantidad total de movimientos de caja del día.
      ingresos_count    — cantidad de movimientos positivos.
      devoluciones_count— cantidad de movimientos negativos.
    """

    date = serializers.CharField(
        help_text="Fecha del resumen en formato YYYY-MM-DD (hora Buenos Aires).",
    )
    total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Neto del día: suma de todos los movimientos (ingresos + devoluciones).",
    )
    ingresos = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Suma de movimientos con amount > 0 (señas confirmadas).",
    )
    devoluciones = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Suma de movimientos con amount < 0 (devoluciones por cancelación, valor negativo).",
    )
    movements_count = serializers.IntegerField(
        help_text="Cantidad total de movimientos de caja del día.",
    )
    ingresos_count = serializers.IntegerField(
        help_text="Cantidad de movimientos positivos.",
    )
    devoluciones_count = serializers.IntegerField(
        help_text="Cantidad de movimientos negativos.",
    )


class BookingsTodaySummarySerializer(serializers.Serializer):
    """
    Conteos de reservas de hoy por estado.

    Parte del payload del DashboardSerializer.
    Todos los campos son enteros >= 0; total es la suma de los 4 estados.
    """

    pending_payment = serializers.IntegerField(
        help_text="Reservas del día en estado PENDING_PAYMENT.",
    )
    confirmed = serializers.IntegerField(
        help_text="Reservas del día en estado CONFIRMED.",
    )
    completed = serializers.IntegerField(
        help_text="Reservas del día en estado COMPLETED.",
    )
    cancelled = serializers.IntegerField(
        help_text="Reservas del día en estado CANCELLED.",
    )
    total = serializers.IntegerField(
        help_text="Suma de todos los estados (pending + confirmed + completed + cancelled).",
    )


class DashboardSerializer(serializers.Serializer):
    """
    Resumen del día para el panel de inicio del admin.

    Campos:
      bookings_today    — conteos de reservas de hoy por estado.
      courts_total      — cantidad de canchas activas del tenant.
      courts_occupied_now — canchas con booking CONFIRMED que cubren el momento actual.
      cashbox_today     — resumen diario de caja (misma estructura que /api/cash-movements/summary/).

    Solo lectura; todos los datos los provee get_dashboard_summary() (selectors.py).
    """

    bookings_today = BookingsTodaySummarySerializer(
        help_text="Conteos de reservas del día por estado.",
    )
    courts_total = serializers.IntegerField(
        help_text="Cantidad de canchas activas en el tenant.",
    )
    courts_occupied_now = serializers.IntegerField(
        help_text="Canchas con reserva CONFIRMED que cubren el momento actual.",
    )
    cashbox_today = CashDailySummarySerializer(
        help_text="Resumen de caja del día: neto, ingresos, devoluciones y conteos.",
    )
