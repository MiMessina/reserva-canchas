"""
Selectors (queries de lectura) — app bookings

Los selectors encapsulan queries de lectura complejas, separando la lógica
de consulta de las views (ARCHITECTURE.md §4).

Funciones exportadas:
  get_availability(court, date_str) -> list[dict]
    Calcula los slots disponibles para una cancha en una fecha (hora BA).
    Usado por AvailabilityView (GET /api/courts/{id}/availability/?date=YYYY-MM-DD).

  get_daily_cash_summary(date_str) -> dict
    Agrega totales del día (neto, ingresos, devoluciones) desde CashMovement.
    Usado por CashMovementViewSet.summary (GET /api/cash-movements/summary/).

  get_dashboard_summary() -> dict
    Resumen del día para el panel de inicio del admin: bookings de hoy por estado,
    canchas activas y ocupadas ahora, y caja del día.
    Usado por DashboardView (GET /api/dashboard/).

  get_daily_grid(date_str) -> dict
    Grilla multi-cancha del día para el panel de administración.
    Retorna todas las canchas activas con sus slots y el estado de cada uno.
    Usado por DailyGridView (GET /api/bookings/daily-grid/).

Zona horaria:
  date_str está en hora Buenos Aires (lo que el jugador ve).
  Los slots se retornan en UTC (ISO 8601) para que el frontend convierta.
"""

from datetime import datetime, timedelta, date as date_type
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Count, Q, Sum

from apps.bookings.models import Booking, CashMovement
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


def get_daily_cash_summary(date_str: str) -> dict:
    """
    Calcula el resumen diario de caja para una fecha dada.

    Parámetros:
      date_str — fecha en formato "YYYY-MM-DD" en hora Buenos Aires.

    Retorna dict con:
      date              — date_str original.
      total             — neto del día (ingresos + devoluciones).
      ingresos          — suma de movimientos con amount > 0.
      devoluciones      — suma de movimientos con amount < 0 (negativo).
      movements_count   — cantidad total de movimientos.
      ingresos_count    — cantidad de movimientos positivos.
      devoluciones_count— cantidad de movimientos negativos.

    Lanza ValueError si date_str no es un formato de fecha válido.

    Solo incluye movimientos de reservas activas (is_active=True en la Booking
    relacionada) para respetar el soft-delete (RULES.md §4).
    """
    # Lanza ValueError si el formato es inválido (capturado en la view)
    date = date_type.fromisoformat(date_str)

    # Rango completo del día en Buenos Aires convertido a UTC para filtrar
    # created_at de CashMovement (igual que el filtro de list())
    day_start_ba = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=BUENOS_AIRES)
    day_end_ba = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=BUENOS_AIRES)
    day_start_utc = day_start_ba.astimezone(UTC)
    day_end_utc = day_end_ba.astimezone(UTC)

    result = CashMovement.objects.filter(
        booking__is_active=True,
        created_at__gte=day_start_utc,
        created_at__lte=day_end_utc,
    ).aggregate(
        total=Sum("amount"),
        ingresos=Sum("amount", filter=Q(amount__gt=0)),
        devoluciones=Sum("amount", filter=Q(amount__lt=0)),
        movements_count=Count("id"),
        ingresos_count=Count("id", filter=Q(amount__gt=0)),
        devoluciones_count=Count("id", filter=Q(amount__lt=0)),
    )

    zero = Decimal("0")
    return {
        "date": date_str,
        "total": result["total"] if result["total"] is not None else zero,
        "ingresos": result["ingresos"] if result["ingresos"] is not None else zero,
        "devoluciones": result["devoluciones"] if result["devoluciones"] is not None else zero,
        "movements_count": result["movements_count"] or 0,
        "ingresos_count": result["ingresos_count"] or 0,
        "devoluciones_count": result["devoluciones_count"] or 0,
    }


def get_dashboard_summary() -> dict:
    """
    Calcula el resumen del día para el panel de inicio del admin.

    Retorna dict con:
      bookings_today   — conteos de reservas de hoy por estado (pending_payment,
                         confirmed, completed, cancelled, total).
      courts_total     — cantidad de canchas activas en el tenant.
      courts_occupied_now — canchas con booking CONFIRMED que cubren el momento
                         actual (start_dt <= now_utc < end_dt), contadas de forma
                         distinta por court.
      cashbox_today    — resultado de get_daily_cash_summary() para hoy en BA.

    No recibe parámetros: "hoy" se calcula en el momento de la llamada
    usando America/Argentina/Buenos_Aires para la fecha y UTC para los rangos.

    La lógica de lectura vive aquí (selector); ninguna regla de negocio.
    """
    now_utc = datetime.now(UTC)
    today_ba_str = now_utc.astimezone(BUENOS_AIRES).date().isoformat()

    # Rango completo del día de hoy en BA → convertido a UTC para filtrar start_dt
    today_ba = now_utc.astimezone(BUENOS_AIRES).date()
    day_start_ba = datetime(today_ba.year, today_ba.month, today_ba.day, 0, 0, 0, tzinfo=BUENOS_AIRES)
    day_end_ba = datetime(today_ba.year, today_ba.month, today_ba.day, 23, 59, 59, tzinfo=BUENOS_AIRES)
    day_start_utc = day_start_ba.astimezone(UTC)
    day_end_utc = day_end_ba.astimezone(UTC)

    # Conteos de reservas de hoy por estado (una sola query con anotaciones condicionales)
    counts = Booking.objects.filter(
        is_active=True,
        start_dt__gte=day_start_utc,
        start_dt__lte=day_end_utc,
    ).aggregate(
        pending_payment=Count("id", filter=Q(status=Booking.Status.PENDING_PAYMENT)),
        confirmed=Count("id", filter=Q(status=Booking.Status.CONFIRMED)),
        completed=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
        total=Count("id"),
    )

    # Canchas con booking CONFIRMED que cubren right now (solapamiento [start, end))
    courts_occupied_now = (
        Booking.objects.filter(
            is_active=True,
            status=Booking.Status.CONFIRMED,
            start_dt__lte=now_utc,
            end_dt__gt=now_utc,
        )
        .values("court")
        .distinct()
        .count()
    )

    # Total de canchas activas en el tenant
    courts_total = Court.objects.filter(is_active=True).count()

    # Reutilizar selector de caja (no duplicar lógica — RULES.md §1)
    cashbox_today = get_daily_cash_summary(today_ba_str)

    return {
        "bookings_today": {
            "pending_payment": counts["pending_payment"] or 0,
            "confirmed": counts["confirmed"] or 0,
            "completed": counts["completed"] or 0,
            "cancelled": counts["cancelled"] or 0,
            "total": counts["total"] or 0,
        },
        "courts_total": courts_total,
        "courts_occupied_now": courts_occupied_now,
        "cashbox_today": cashbox_today,
    }


def get_daily_grid(date_str: str) -> dict:
    """
    Calcula la grilla multi-cancha del día para el panel de administración.

    A diferencia de get_availability(), este selector:
      - Incluye TODAS las canchas activas (no solo una).
      - NO filtra slots pasados (el admin ve el día completo).
      - Incluye el status real de cada slot (AVAILABLE, PENDING_PAYMENT, CONFIRMED, COMPLETED).
      - Incluye booking_id, guest_name y price cuando hay reserva.
      - Considera PENDING_PAYMENT, CONFIRMED y COMPLETED como ocupados
        (CANCELLED libera el slot).

    Parámetros:
      date_str — fecha en formato "YYYY-MM-DD" en hora Buenos Aires.

    Retorna dict con:
      date   — date_str original.
      courts — lista de canchas activas con sus slots del día.

    Lanza ValueError si date_str no es un formato de fecha válido.
    """
    # Lanza ValueError si el formato es inválido (capturado en la view)
    date = date_type.fromisoformat(date_str)
    weekday = date.weekday()  # 0=lunes, coincide con ScheduleBlock.Weekday

    # Rango completo del día en Buenos Aires convertido a UTC
    day_start_ba = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=BUENOS_AIRES)
    day_end_ba = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=BUENOS_AIRES)
    day_start_utc = day_start_ba.astimezone(UTC)
    day_end_utc = day_end_ba.astimezone(UTC)

    courts = Court.objects.filter(is_active=True).order_by("name")

    # Prefetch bloques horarios activos del weekday para todas las canchas
    # (una sola query en lugar de N+1)
    blocks_by_court: dict[int, list] = {}
    all_blocks = ScheduleBlock.objects.filter(
        court__in=courts,
        weekday=weekday,
        is_active=True,
    ).order_by("court_id", "open_time")
    for block in all_blocks:
        blocks_by_court.setdefault(block.court_id, []).append(block)

    # Prefetch reservas activas del día para todas las canchas de una sola vez
    # Incluimos PENDING_PAYMENT, CONFIRMED y COMPLETED (CANCELLED libera el slot)
    bookings_qs = (
        Booking.objects.filter(
            court__in=courts,
            is_active=True,
            status__in=[
                Booking.Status.PENDING_PAYMENT,
                Booking.Status.CONFIRMED,
                Booking.Status.COMPLETED,
            ],
            start_dt__gte=day_start_utc,
            start_dt__lte=day_end_utc,
        )
        .values(
            "id",
            "court_id",
            "start_dt",
            "end_dt",
            "status",
            "guest_name",
            "price",
            "user_id",
            "user__email",
            "user__first_name",
            "user__last_name",
        )
    )

    bookings_by_court: dict[int, list] = {}
    for booking in bookings_qs:
        bookings_by_court.setdefault(booking["court_id"], []).append(booking)

    courts_data = []
    for court in courts:
        court_blocks = blocks_by_court.get(court.pk, [])
        court_bookings = bookings_by_court.get(court.pk, [])

        duration = timedelta(minutes=court.slot_duration_minutes)
        slots = []

        for block in court_blocks:
            current_ba = datetime.combine(date, block.open_time, tzinfo=BUENOS_AIRES)
            block_end_ba = datetime.combine(date, block.close_time, tzinfo=BUENOS_AIRES)

            while current_ba + duration <= block_end_ba:
                end_ba = current_ba + duration
                start_utc = current_ba.astimezone(UTC)
                end_utc = end_ba.astimezone(UTC)

                # Buscar reserva solapada: start_dt < end_utc AND end_dt > start_utc
                overlapping = next(
                    (
                        b for b in court_bookings
                        if b["start_dt"] < end_utc and b["end_dt"] > start_utc
                    ),
                    None,
                )

                if overlapping:
                    # Determinar guest_name: campo directo o email del usuario
                    if overlapping["guest_name"]:
                        guest_display = overlapping["guest_name"]
                    elif overlapping["user_id"]:
                        first = overlapping["user__first_name"] or ""
                        last = overlapping["user__last_name"] or ""
                        full = f"{first} {last}".strip()
                        guest_display = full if full else overlapping["user__email"]
                    else:
                        guest_display = None

                    slots.append({
                        "start_dt": start_utc.isoformat(),
                        "end_dt": end_utc.isoformat(),
                        "status": overlapping["status"],
                        "booking_id": overlapping["id"],
                        "guest_name": guest_display,
                        "price": str(overlapping["price"]) if overlapping["price"] is not None else None,
                    })
                else:
                    slots.append({
                        "start_dt": start_utc.isoformat(),
                        "end_dt": end_utc.isoformat(),
                        "status": "AVAILABLE",
                        "booking_id": None,
                        "guest_name": None,
                        "price": None,
                    })

                current_ba = end_ba

        courts_data.append({
            "id": court.pk,
            "name": court.name,
            "type": court.court_type,
            "slot_duration_minutes": court.slot_duration_minutes,
            "slots": slots,
        })

    return {
        "date": date_str,
        "courts": courts_data,
    }
