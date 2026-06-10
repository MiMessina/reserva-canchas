"""
Modelos — app cashbox

ADR-011: CashSession hereda de TimeStampedSoftDeleteModel (is_active, created_at, updated_at).

Nota sobre CashMovement:
  El modelo CashMovement vive en apps.bookings.models (fue creado en Sprint 2 junto
  al motor de reservas). Se importa desde allí donde se necesite; no se redefine aquí.

Reglas de datos (RULES.md §4, DER.md):
  - Soft-delete obligatorio en CashSession via is_active (heredado). Prohibido DELETE físico.
  - Fechas/horas en UTC (USE_TZ=True en settings).
  - Una sola sesión de caja por día por tenant (unique_together en session_date).
    El aislamiento multi-tenant por esquema garantiza que la unicidad sea por tenant.
"""

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedSoftDeleteModel


class CashSession(TimeStampedSoftDeleteModel):
    """
    Sesión de caja diaria del complejo.

    Registro INFORMATIVO que envuelve los movimientos del día. No bloquea
    la creación de CashMovement: los movimientos se registran independientemente.
    La sesión permite al cajero declarar apertura/cierre y controlar diferencias.

    Ciclo de vida:
      OPEN   → el cajero abrió la caja declarando el efectivo inicial.
      CLOSED → el cajero cerró la caja registrando el monto contado y las diferencias.

    Restricción DB:
      unique_together = ('session_date',) — una sesión por día por tenant.
      (django-tenants garantiza el aislamiento por esquema.)
    """

    STATUS_OPEN = "OPEN"
    STATUS_CLOSED = "CLOSED"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Abierta"),
        (STATUS_CLOSED, "Cerrada"),
    ]

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cash_sessions",
        verbose_name="Operador",
        help_text="Usuario (operator o tenant_admin) que abrió la sesión de caja.",
    )
    session_date = models.DateField(
        verbose_name="Fecha de caja",
        help_text=(
            "Día de la sesión de caja, en hora Buenos Aires "
            "(America/Argentina/Buenos_Aires). Solo una sesión por día por tenant."
        ),
    )
    opened_at = models.DateTimeField(
        verbose_name="Abierta en (UTC)",
        help_text="Timestamp UTC de apertura de la sesión.",
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Cerrada en (UTC)",
        help_text="Timestamp UTC de cierre. Null mientras la sesión esté abierta.",
    )
    opening_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto inicial",
        help_text="Efectivo declarado en caja al momento de la apertura.",
    )
    closing_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto contado al cierre",
        help_text="Efectivo físico contado por el cajero al cerrar la sesión.",
    )
    expected_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto esperado",
        help_text=(
            "Calculado al cerrar: opening_amount + suma de CashMovement.amount "
            "del día. Sirve como referencia para detectar diferencias."
        ),
    )
    difference = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diferencia",
        help_text="closing_amount - expected_amount. Negativo = faltante; positivo = sobrante.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Observaciones",
        help_text="Notas del cajero al cerrar la sesión (diferencias, incidentes, etc.).",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        verbose_name="Estado",
        help_text="OPEN: sesión abierta. CLOSED: sesión cerrada.",
    )

    class Meta:
        verbose_name = "Sesión de caja"
        verbose_name_plural = "Sesiones de caja"
        ordering = ["-session_date"]
        # Una sesión por día por tenant (el esquema aísla por tenant)
        unique_together = [("session_date",)]

    def __str__(self):
        return f"CashSession {self.session_date} [{self.status}] — {self.operator}"
