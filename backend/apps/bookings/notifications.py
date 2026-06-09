"""
notifications.py — Notificaciones por email del módulo bookings.

Envía emails transaccionales a jugadores (registrados o invitados) cuando
cambia el estado de su reserva.

Funciones exportadas:
  notify_booking_created(booking)   — PENDING_PAYMENT: reserva recibida.
  notify_booking_confirmed(booking) — CONFIRMED: reserva confirmada.
  notify_booking_cancelled(booking) — CANCELLED: reserva cancelada.

Reglas:
  - Se obtiene el email del destinatario: booking.user.email (registrado) o
    booking.guest_email (invitado). Si no hay email, se omite el envío.
  - Todas las funciones están envueltas en try/except: un error de email
    nunca debe romper el flujo de negocio (la reserva ya fue guardada).
  - Las horas se muestran en America/Argentina/Buenos_Aires.
  - Envío sincrónico (no Celery — post-MVP).

Regla crítica de integración (services.py):
  Llamar FUERA del bloque transaction.atomic() para que el email
  solo se envíe después de que el commit sea exitoso. Un rollback
  dentro de la transacción no debe disparar un email.
"""

import logging
from zoneinfo import ZoneInfo

from django.core.mail import send_mail

logger = logging.getLogger(__name__)

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")

# Nombres de días y meses en español para el formateo amigable de fechas.
_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_recipient(booking):
    """
    Obtiene el email y nombre del destinatario de la notificación.

    Para reserva de usuario registrado usa booking.user.email y su nombre completo.
    Para reserva de invitado usa booking.guest_email y booking.guest_name.

    Retorna (email, nombre). Si email está vacío retorna (None, None) y el
    llamador debe omitir el envío.
    """
    if booking.user is not None:
        email = booking.user.email or ""
        nombre = booking.user.get_full_name() or booking.user.email or ""
    else:
        email = booking.guest_email or ""
        nombre = booking.guest_name or ""

    if not email.strip():
        return None, None

    return email.strip(), nombre.strip()


def _format_datetime_ba(dt):
    """
    Convierte un datetime UTC a America/Argentina/Buenos_Aires y retorna
    un string amigable en español.

    Ejemplo: "Lunes 9 de junio de 2026 a las 19:00"
    """
    dt_ba = dt.astimezone(BUENOS_AIRES)
    dia_semana = _DIAS[dt_ba.weekday()]
    mes = _MESES[dt_ba.month - 1]
    return f"{dia_semana} {dt_ba.day} de {mes} de {dt_ba.year} a las {dt_ba.strftime('%H:%M')}"


def _format_time_ba(dt):
    """
    Retorna solo la hora en Buenos Aires en formato HH:MM.
    """
    return dt.astimezone(BUENOS_AIRES).strftime("%H:%M")


# ---------------------------------------------------------------------------
# Funciones exportadas
# ---------------------------------------------------------------------------

def notify_booking_created(booking) -> None:
    """
    Envía email de confirmación de recepción al crearse una reserva (PENDING_PAYMENT).

    Fire-and-forget: cualquier excepción se loguea pero no se propaga,
    ya que la reserva ya fue persistida en la DB.
    """
    try:
        email, nombre = _get_recipient(booking)
        if not email:
            logger.debug(
                "notify_booking_created: booking_id=%s sin email destinatario — se omite.",
                booking.pk,
            )
            return

        court_name = booking.court.name
        fecha_str = _format_datetime_ba(booking.start_dt)
        hora_inicio = _format_time_ba(booking.start_dt)
        hora_fin = _format_time_ba(booking.end_dt)

        asunto = f"Reserva recibida — {court_name}"
        cuerpo = (
            f"Hola {nombre},\n\n"
            f"Recibimos tu reserva:\n\n"
            f"  Cancha:  {court_name}\n"
            f"  Fecha:   {fecha_str}\n"
            f"  Horario: {hora_inicio} – {hora_fin}\n"
            f"  Precio:  ${booking.price}\n\n"
            f"Tu reserva está pendiente de confirmación. "
            f"Te avisaremos cuando el equipo verifique la seña.\n\n"
            f"¡Gracias por reservar!\n"
            f"El equipo de CanchaYA"
        )

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=None,  # usa DEFAULT_FROM_EMAIL de settings
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(
            "notify_booking_created: email enviado a=%s booking_id=%s",
            email,
            booking.pk,
        )

    except Exception:
        logger.exception(
            "notify_booking_created: error enviando email: booking_id=%s",
            booking.pk,
        )


def notify_booking_confirmed(booking) -> None:
    """
    Envía email de confirmación al transicionar la reserva a CONFIRMED.

    Fire-and-forget: cualquier excepción se loguea pero no se propaga.
    """
    try:
        email, nombre = _get_recipient(booking)
        if not email:
            logger.debug(
                "notify_booking_confirmed: booking_id=%s sin email destinatario — se omite.",
                booking.pk,
            )
            return

        court_name = booking.court.name
        fecha_str = _format_datetime_ba(booking.start_dt)
        hora_inicio = _format_time_ba(booking.start_dt)
        hora_fin = _format_time_ba(booking.end_dt)

        asunto = f"¡Reserva confirmada! — {court_name}"
        cuerpo = (
            f"Hola {nombre},\n\n"
            f"¡Tu reserva fue confirmada! Te esperamos.\n\n"
            f"  Cancha:  {court_name}\n"
            f"  Fecha:   {fecha_str}\n"
            f"  Horario: {hora_inicio} – {hora_fin}\n"
            f"  Precio:  ${booking.price}\n\n"
            f"¡Nos vemos!\n"
            f"El equipo de CanchaYA"
        )

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(
            "notify_booking_confirmed: email enviado a=%s booking_id=%s",
            email,
            booking.pk,
        )

    except Exception:
        logger.exception(
            "notify_booking_confirmed: error enviando email: booking_id=%s",
            booking.pk,
        )


def notify_booking_cancelled(booking) -> None:
    """
    Envía email informando la cancelación de la reserva.

    Fire-and-forget: cualquier excepción se loguea pero no se propaga.
    """
    try:
        email, nombre = _get_recipient(booking)
        if not email:
            logger.debug(
                "notify_booking_cancelled: booking_id=%s sin email destinatario — se omite.",
                booking.pk,
            )
            return

        court_name = booking.court.name
        fecha_str = _format_datetime_ba(booking.start_dt)
        hora_inicio = _format_time_ba(booking.start_dt)
        hora_fin = _format_time_ba(booking.end_dt)
        motivo = booking.cancellation_reason or "Sin motivo especificado."

        asunto = f"Reserva cancelada — {court_name}"
        cuerpo = (
            f"Hola {nombre},\n\n"
            f"Te informamos que tu reserva fue cancelada.\n\n"
            f"  Cancha:  {court_name}\n"
            f"  Fecha:   {fecha_str}\n"
            f"  Horario: {hora_inicio} – {hora_fin}\n"
            f"  Motivo:  {motivo}\n\n"
            f"Si tenés dudas, contactá al complejo.\n"
            f"El equipo de CanchaYA"
        )

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(
            "notify_booking_cancelled: email enviado a=%s booking_id=%s",
            email,
            booking.pk,
        )

    except Exception:
        logger.exception(
            "notify_booking_cancelled: error enviando email: booking_id=%s",
            booking.pk,
        )
