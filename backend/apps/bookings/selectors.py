"""
Selectors (queries de lectura) — app bookings

Sprint 0: placeholder.

Expansión Sprint 1+:
  - get_booking_by_id(booking_id: int) -> Booking
  - list_bookings_by_court(court, date_from, date_to) -> QuerySet[Booking]
  - list_bookings_by_user(user) -> QuerySet[Booking]
  - list_active_bookings_for_slot(court, start_dt, end_dt) -> QuerySet[Booking]
    (usado por el motor para detectar overbooking — corre dentro de la transacción)
"""
