"""
tools.py — Definiciones y ejecutores de tools para el agente IA (ADR-012).

Las definiciones se pasan al Claude API (input_schema).
Los ejecutores llaman directamente a services.py y selectors.py.

Tools disponibles:
  get_availability   — slots libres de una o todas las canchas en una fecha
  create_booking     — crea reserva PENDING_PAYMENT para jugador invitado
  cancel_booking     — cancela la reserva activa del jugador por teléfono
  get_my_booking     — consulta el estado de la reserva activa del jugador
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from rest_framework.exceptions import ValidationError

from apps.bookings.models import Booking
from apps.bookings.selectors import get_availability as _get_availability
from apps.bookings.services import cancel_booking as _cancel_booking
from apps.bookings.services import create_booking as _create_booking
from apps.courts.models import Court

logger = logging.getLogger(__name__)

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")

# ---------------------------------------------------------------------------
# Definiciones de tools para Claude API
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_availability",
        "description": (
            "Consulta los turnos disponibles de una o todas las canchas para una fecha dada. "
            "Usá esta tool cuando el jugador pregunta por disponibilidad, horarios libres o quiere saber qué canchas tiene disponibles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Fecha en formato YYYY-MM-DD (hora de Buenos Aires).",
                },
                "court_id": {
                    "type": "integer",
                    "description": "ID de una cancha específica. Omitir para consultar todas las canchas activas.",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "create_booking",
        "description": (
            "Crea una reserva para el jugador. "
            "La reserva queda en estado PENDING_PAYMENT. "
            "Usá esta tool cuando el jugador confirmó cancha, fecha, hora y sus datos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "court_id": {
                    "type": "integer",
                    "description": "ID de la cancha a reservar.",
                },
                "date": {
                    "type": "string",
                    "description": "Fecha en formato YYYY-MM-DD (hora de Buenos Aires).",
                },
                "time": {
                    "type": "string",
                    "description": "Hora de inicio en formato HH:MM, 24hs (hora de Buenos Aires). Ejemplo: '20:00'.",
                },
                "guest_name": {
                    "type": "string",
                    "description": "Nombre completo del jugador.",
                },
                "guest_phone": {
                    "type": "string",
                    "description": "Teléfono del jugador (número de WhatsApp).",
                },
            },
            "required": ["court_id", "date", "time", "guest_name", "guest_phone"],
        },
    },
    {
        "name": "cancel_booking",
        "description": (
            "Cancela la reserva activa (PENDING_PAYMENT o CONFIRMED) del jugador identificado por su teléfono. "
            "Usá esta tool cuando el jugador quiere cancelar su reserva."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "guest_phone": {
                    "type": "string",
                    "description": "Teléfono del jugador (el mismo que usó al reservar).",
                },
                "reason": {
                    "type": "string",
                    "description": "Motivo de cancelación (opcional, puede ser vacío).",
                },
            },
            "required": ["guest_phone"],
        },
    },
    {
        "name": "get_my_booking",
        "description": (
            "Consulta la reserva activa del jugador identificado por su teléfono. "
            "Usá esta tool cuando el jugador pregunta por el estado de su reserva, su turno, o quiere saber si tiene algo reservado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "guest_phone": {
                    "type": "string",
                    "description": "Teléfono del jugador.",
                },
            },
            "required": ["guest_phone"],
        },
    },
]


# ---------------------------------------------------------------------------
# Ejecutores de tools
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Despacha la llamada al ejecutor correspondiente y retorna
    el resultado como string (se pasa como tool_result a Claude).
    Los errores se capturan y se devuelven como texto descriptivo
    para que Claude los entienda y comunique al usuario.
    """
    executors = {
        "get_availability": _execute_get_availability,
        "create_booking": _execute_create_booking,
        "cancel_booking": _execute_cancel_booking,
        "get_my_booking": _execute_get_my_booking,
    }
    executor = executors.get(tool_name)
    if not executor:
        return f"Error: tool '{tool_name}' no encontrada."
    try:
        return executor(tool_input)
    except ValidationError as exc:
        # Errores de negocio del service layer (SLOT_ALREADY_BOOKED, etc.)
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            err = detail["error"]
            return f"Error de negocio [{err.get('code', 'ERROR')}]: {err.get('message', str(detail))}"
        return f"Error de validación: {str(detail)}"
    except Exception as exc:
        logger.exception("Error inesperado en tool '%s': %s", tool_name, exc)
        return f"Error inesperado al ejecutar '{tool_name}': {str(exc)}"


def _execute_get_availability(inp: dict) -> str:
    date_str: str = inp["date"]
    court_id: int | None = inp.get("court_id")

    if court_id:
        courts = Court.objects.filter(pk=court_id, is_active=True)
    else:
        courts = Court.objects.filter(is_active=True)

    if not courts.exists():
        return "No hay canchas activas disponibles."

    lines = []
    for court in courts:
        slots = _get_availability(court, date_str)
        available = [s for s in slots if s["is_available"]]
        if available:
            times = ", ".join(
                datetime.fromisoformat(s["start_dt"])
                .astimezone(BUENOS_AIRES)
                .strftime("%H:%M")
                for s in available
            )
            lines.append(f"- {court.name} (ID {court.pk}, {court.get_court_type_display()}): {times}")
        else:
            lines.append(f"- {court.name} (ID {court.pk}): sin turnos disponibles para esa fecha.")

    return "Turnos disponibles para el " + date_str + ":\n" + "\n".join(lines)


def _execute_create_booking(inp: dict) -> str:
    court_id: int = inp["court_id"]
    date_str: str = inp["date"]
    time_str: str = inp["time"]
    guest_name: str = inp["guest_name"]
    guest_phone: str = inp["guest_phone"]

    # Parsear fecha + hora en BA y convertir a UTC timezone-aware
    hour, minute = map(int, time_str.split(":"))
    year, month, day = map(int, date_str.split("-"))
    start_dt_ba = datetime(year, month, day, hour, minute, tzinfo=BUENOS_AIRES)
    start_dt_utc = start_dt_ba.astimezone(ZoneInfo("UTC"))

    booking = _create_booking(
        court_id=court_id,
        start_dt=start_dt_utc,
        guest_name=guest_name,
        guest_phone=guest_phone,
    )

    start_ba = booking.start_dt.astimezone(BUENOS_AIRES)
    end_ba = booking.end_dt.astimezone(BUENOS_AIRES)
    return (
        f"Reserva creada exitosamente.\n"
        f"- ID: {booking.pk}\n"
        f"- Cancha: {booking.court.name}\n"
        f"- Fecha y hora: {start_ba.strftime('%d/%m/%Y %H:%M')} a {end_ba.strftime('%H:%M')}\n"
        f"- Precio: ${booking.price}\n"
        f"- Estado: Pendiente de pago de seña\n"
        f"El cajero del complejo confirmará la reserva al recibir la transferencia."
    )


def _execute_cancel_booking(inp: dict) -> str:
    guest_phone: str = inp["guest_phone"]
    reason: str = inp.get("reason", "Cancelado por el jugador via chat.")

    booking = (
        Booking.objects.filter(
            guest_phone=guest_phone,
            is_active=True,
            status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED],
        )
        .order_by("-created_at")
        .first()
    )

    if not booking:
        return f"No se encontró ninguna reserva activa para el teléfono {guest_phone}."

    start_ba = booking.start_dt.astimezone(BUENOS_AIRES)
    _cancel_booking(booking=booking, cancelled_by=None, reason=reason)

    return (
        f"Reserva cancelada correctamente.\n"
        f"- Cancha: {booking.court.name}\n"
        f"- Turno: {start_ba.strftime('%d/%m/%Y %H:%M')}\n"
        f"- Motivo: {reason}"
    )


def _execute_get_my_booking(inp: dict) -> str:
    guest_phone: str = inp["guest_phone"]

    bookings = Booking.objects.filter(
        guest_phone=guest_phone,
        is_active=True,
        status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED],
    ).order_by("-created_at")

    if not bookings.exists():
        return f"No encontré reservas activas para el teléfono {guest_phone}."

    lines = []
    for b in bookings[:3]:
        start_ba = b.start_dt.astimezone(BUENOS_AIRES)
        status_label = {
            Booking.Status.PENDING_PAYMENT: "Pendiente de pago",
            Booking.Status.CONFIRMED: "Confirmada",
        }.get(b.status, b.status)
        lines.append(
            f"- Cancha: {b.court.name} | {start_ba.strftime('%d/%m/%Y %H:%M')} | Estado: {status_label} | ID: {b.pk}"
        )

    return "Tus reservas activas:\n" + "\n".join(lines)
