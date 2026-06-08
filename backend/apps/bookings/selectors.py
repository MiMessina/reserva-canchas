"""
Selectors (queries de lectura) — app bookings

Los selectors encapsulan queries de lectura complejas, separando la lógica
de consulta de las views (ARCHITECTURE.md §4).

Funciones exportadas:
  get_availability(court, date_str) -> list[dict]
    Calcula los slots disponibles para una cancha en una fecha (hora BA).
    Usado por AvailabilityView (GET /api/courts/{id}/availability/?date=YYYY-MM-DD).

Zona horaria:
  date_str está en hora Buenos Aires (lo que el jugador ve).
  Los slots se retornan en UTC (ISO 8601) para que el frontend convierta.
"""

from datetime import datetime, timedelta, date as date_type
from zoneinfo import ZoneInfo

from apps.bookings.models import Booking
from apps.courts.models import Court, ScheduleBlock

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")
UTC = ZoneInfo("UTC")


def get_availability(court: Court, date_str: str) -> list[dict]:
    """
    Calcula los slots disponibles para una cancha en una fecha.

    Parámetros:
      court    — instancia Court activa.
      date_str — fecha en formato "YYYY-MM-DD" en hora Buenos Aires.

    Retorna lista de dicts con:
      start_dt    — ISO 8601 en UTC (con offset +00:00).
      end_dt      — ISO 8601 en UTC.
      is_available — bool: True si el slot no tiene reserva activa solapada.

    Lanza ValueError si date_str no es un formato de fecha válido.

    Algoritmo:
      1. Obtener todos los ScheduleBlocks activos de la cancha para el weekday.
      2. Obtener todas las reservas activas (PENDING_PAYMENT o CONFIRMED)
         del día en esa cancha.
      3. Para cada bloque, generar slots de duración court.slot_duration_minutes.
      4. Marcar cada slot como disponible si no hay solapamiento con reserva.
    """
    # Lanza ValueError si el formato es inválido (capturado en la view)
    date = date_type.fromisoformat(date_str)
    weekday = date.weekday()  # 0=lunes, coincide con ScheduleBlock.Weekday

    blocks = ScheduleBlock.objects.filter(
        court=court,
        weekday=weekday,
        is_active=True,
    ).order_by("open_time")

    if not blocks.exists():
        return []

    # Rango completo del día en Buenos Aires convertido a UTC para filtrar bookings
    day_start_ba = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=BUENOS_AIRES)
    day_end_ba = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=BUENOS_AIRES)
    day_start_utc = day_start_ba.astimezone(UTC)
    day_end_utc = day_end_ba.astimezone(UTC)

    # Reservas activas del día en esa cancha (lista en memoria para comparar)
    booked = list(
        Booking.objects.filter(
            court=court,
            is_active=True,
            status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED],
            start_dt__gte=day_start_utc,
            start_dt__lte=day_end_utc,
        ).values("start_dt", "end_dt")
    )

    duration = timedelta(minutes=court.slot_duration_minutes)
    now_utc = datetime.now(UTC)
    slots = []

    for block in blocks:
        # Construir slots a partir del bloque horario en hora BA
        current_ba = datetime.combine(date, block.open_time, tzinfo=BUENOS_AIRES)
        block_end_ba = datetime.combine(date, block.close_time, tzinfo=BUENOS_AIRES)

        while current_ba + duration <= block_end_ba:
            end_ba = current_ba + duration
            start_utc = current_ba.astimezone(UTC)
            end_utc = end_ba.astimezone(UTC)

            # No mostrar slots que ya comenzaron (jugador no puede reservar el pasado)
            if start_utc <= now_utc:
                current_ba = end_ba
                continue

            # Solapamiento: reserva existente solapa si start < end_utc AND end > start_utc
            is_available = not any(
                b["start_dt"] < end_utc and b["end_dt"] > start_utc
                for b in booked
            )

            slots.append({
                "start_dt": start_utc.isoformat(),
                "end_dt": end_utc.isoformat(),
                "is_available": is_available,
            })

            current_ba = end_ba

    return slots
