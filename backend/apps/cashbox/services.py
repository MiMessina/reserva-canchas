"""
Service layer — app cashbox

Toda lógica de caja vive aquí (RULES.md §4). Nunca en views ni serializers.

Funciones exportadas:
  open_cash_session(*, operator, opening_amount, session_date=None) -> CashSession
  close_cash_session(*, operator, closing_amount, notes='', session_date=None) -> CashSession
  register_cash_movement(*, booking, operator, amount) -> CashMovement  [ver apps.bookings.services]

Validaciones de negocio:
  SESSION_ALREADY_OPEN  — ya existe una sesión OPEN para ese día
  SESSION_NOT_OPEN      — no existe sesión OPEN para ese día al intentar cerrar
  SESSION_ALREADY_CLOSED — la sesión del día ya está CLOSED

Regla CRÍTICA (ADR-003):
  open_cash_session usa select_for_update() para serializar accesos concurrentes
  y evitar race conditions en la apertura.

Zona horaria (RULES.md §4):
  session_date se calcula en America/Argentina/Buenos_Aires.
  opened_at y closed_at se guardan en UTC.
"""

import logging
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.models import CashMovement
from apps.cashbox.models import CashSession

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


def _today_ba() -> date:
    """Retorna la fecha actual en hora Buenos Aires."""
    return timezone.now().astimezone(BUENOS_AIRES).date()


def _calculate_movements_total(session_date: date) -> Decimal:
    """
    Suma los CashMovement.amount del día indicado.

    CashMovement.created_at está en UTC; filtramos por rango UTC equivalente al
    día en Buenos Aires para calcular el expected_amount.
    """
    from datetime import datetime, time
    import datetime as dt_module

    # Construir rango UTC del día en Buenos Aires
    start_of_day_ba = datetime.combine(session_date, time.min, tzinfo=BUENOS_AIRES)
    end_of_day_ba = datetime.combine(
        session_date + dt_module.timedelta(days=1), time.min, tzinfo=BUENOS_AIRES
    )

    result = CashMovement.objects.filter(
        created_at__gte=start_of_day_ba,
        created_at__lt=end_of_day_ba,
    ).aggregate(total=Sum("amount"))

    return result["total"] or Decimal("0.00")


# ---------------------------------------------------------------------------
# open_cash_session
# ---------------------------------------------------------------------------

def open_cash_session(
    *,
    operator,
    opening_amount: Decimal,
    session_date: date | None = None,
) -> CashSession:
    """
    Abre una nueva sesión de caja para el día indicado.

    Parámetros:
      operator       — instancia User (operator o tenant_admin) que abre la caja.
      opening_amount — efectivo inicial declarado (>= 0).
      session_date   — fecha de caja en hora BA; default = hoy en BA.

    Validaciones:
      - Si ya existe una sesión OPEN para ese día → SESSION_ALREADY_OPEN.

    Usa select_for_update() para evitar race conditions en apertura concurrente.

    Retorna la instancia CashSession creada.
    """
    if session_date is None:
        session_date = _today_ba()

    with transaction.atomic():
        # Bloqueo pesimista: serializa accesos concurrentes al mismo día.
        # select_for_update no funciona sobre un queryset vacío de forma directa;
        # usamos filter + select_for_update para bloquear filas existentes.
        existing_sessions = CashSession.objects.select_for_update().filter(
            session_date=session_date,
            is_active=True,
        )

        if existing_sessions.filter(status=CashSession.STATUS_OPEN).exists():
            raise ValidationError(
                _build_error(
                    "SESSION_ALREADY_OPEN",
                    f"Ya existe una sesión de caja abierta para el {session_date}.",
                    {"session_date": str(session_date)},
                )
            )

        session = CashSession.objects.create(
            operator=operator,
            session_date=session_date,
            opened_at=timezone.now(),
            opening_amount=opening_amount,
            status=CashSession.STATUS_OPEN,
        )

    logger.info(
        "Sesión de caja abierta: id=%s operator=%s session_date=%s opening_amount=%s",
        session.pk,
        operator.pk,
        session_date,
        opening_amount,
    )
    return session


# ---------------------------------------------------------------------------
# close_cash_session
# ---------------------------------------------------------------------------

def close_cash_session(
    *,
    operator,
    closing_amount: Decimal,
    notes: str = "",
    session_date: date | None = None,
) -> CashSession:
    """
    Cierra la sesión de caja abierta del día indicado.

    Parámetros:
      operator       — instancia User (operator o tenant_admin) que cierra la caja.
      closing_amount — efectivo físico contado al cierre (>= 0).
      notes          — observaciones del cajero (opcional).
      session_date   — fecha de caja en hora BA; default = hoy en BA.

    Validaciones:
      - Si no existe sesión para ese día → SESSION_NOT_OPEN.
      - Si la sesión ya está CLOSED → SESSION_ALREADY_CLOSED.

    Calcula:
      expected_amount = opening_amount + suma de CashMovement del día
      difference      = closing_amount - expected_amount

    Retorna la instancia CashSession actualizada.
    """
    if session_date is None:
        session_date = _today_ba()

    try:
        session = CashSession.objects.get(
            session_date=session_date,
            is_active=True,
        )
    except CashSession.DoesNotExist:
        raise ValidationError(
            _build_error(
                "SESSION_NOT_OPEN",
                f"No existe una sesión de caja para el {session_date}.",
                {"session_date": str(session_date)},
            )
        )

    if session.status == CashSession.STATUS_CLOSED:
        raise ValidationError(
            _build_error(
                "SESSION_ALREADY_CLOSED",
                f"La sesión de caja del {session_date} ya fue cerrada.",
                {"session_date": str(session_date), "session_id": session.pk},
            )
        )

    # Calcular expected_amount: monto inicial + movimientos del día
    movements_total = _calculate_movements_total(session_date)
    expected_amount = session.opening_amount + movements_total
    difference = closing_amount - expected_amount

    session.closing_amount = closing_amount
    session.expected_amount = expected_amount
    session.difference = difference
    session.notes = notes
    session.closed_at = timezone.now()
    session.status = CashSession.STATUS_CLOSED
    session.save(update_fields=[
        "closing_amount",
        "expected_amount",
        "difference",
        "notes",
        "closed_at",
        "status",
        "updated_at",
    ])

    logger.info(
        "Sesión de caja cerrada: id=%s operator=%s session_date=%s "
        "closing_amount=%s expected_amount=%s difference=%s",
        session.pk,
        operator.pk,
        session_date,
        closing_amount,
        expected_amount,
        difference,
    )
    return session
