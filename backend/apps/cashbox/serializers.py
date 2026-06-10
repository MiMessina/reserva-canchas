"""
Serializers — app cashbox

Los serializers validan estructura, no gobiernan el negocio (RULES.md §1).
La lógica de apertura/cierre de sesión vive en cashbox/services.py.

Serializers exportados:
  CashSessionSerializer        — lectura completa de una sesión de caja.
  OpenCashSessionSerializer    — input para abrir una sesión (POST /open/).
  CloseCashSessionSerializer   — input para cerrar una sesión (POST /close/).
  CashMovementSerializer       — lectura de un movimiento de caja.
  CashDailySummarySerializer   — resumen diario de movimientos de caja.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.bookings.models import CashMovement
from apps.cashbox.models import CashSession


class CashSessionSerializer(serializers.ModelSerializer):
    """Serializer de lectura completa de una sesión de caja."""

    operator_email = serializers.EmailField(source="operator.email", read_only=True)

    class Meta:
        model = CashSession
        fields = [
            "id",
            "operator",
            "operator_email",
            "session_date",
            "opened_at",
            "closed_at",
            "opening_amount",
            "closing_amount",
            "expected_amount",
            "difference",
            "notes",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OpenCashSessionSerializer(serializers.Serializer):
    """
    Input para abrir una sesión de caja.

    Campos:
      opening_amount — efectivo inicial declarado. Requerido, >= 0.
      session_date   — fecha de caja (date). Opcional; default = hoy en BA.
    """

    opening_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        help_text="Efectivo inicial declarado al abrir la caja. Requerido, >= 0.",
    )
    session_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=(
            "Fecha de la sesión (YYYY-MM-DD) en hora Buenos Aires. "
            "Opcional; si se omite, se usa la fecha actual en BA."
        ),
    )


class CloseCashSessionSerializer(serializers.Serializer):
    """
    Input para cerrar una sesión de caja.

    Campos:
      closing_amount — efectivo contado al cierre. Requerido, >= 0.
      notes          — observaciones del cajero. Opcional.
      session_date   — fecha de la sesión a cerrar (YYYY-MM-DD). Opcional; default = hoy en BA.
    """

    closing_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        help_text="Efectivo físico contado al cerrar la caja. Requerido, >= 0.",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Observaciones del cajero al cerrar la sesión (diferencias, incidentes, etc.).",
    )
    session_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=(
            "Fecha de la sesión a cerrar (YYYY-MM-DD) en hora Buenos Aires. "
            "Opcional; si se omite, se usa la fecha actual en BA."
        ),
    )


class CashMovementSerializer(serializers.ModelSerializer):
    """Serializer de lectura de un movimiento de caja."""

    operator_email = serializers.EmailField(source="operator.email", read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)

    class Meta:
        model = CashMovement
        fields = [
            "id",
            "booking_id",
            "operator",
            "operator_email",
            "amount",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class CashDailySummarySerializer(serializers.Serializer):
    """
    Resumen diario de movimientos de caja.

    Solo lectura (no se usa para input).
    """

    date = serializers.DateField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    ingresos = serializers.DecimalField(max_digits=12, decimal_places=2)
    devoluciones = serializers.DecimalField(max_digits=12, decimal_places=2)
    movements_count = serializers.IntegerField()
    ingresos_count = serializers.IntegerField()
    devoluciones_count = serializers.IntegerField()
