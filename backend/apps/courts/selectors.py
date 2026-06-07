"""
Selectors (queries de lectura) — app courts

Sprint 0: placeholder.

Expansión Sprint 1+:
  - get_active_courts() -> QuerySet[Court]
  - get_court_by_id(court_id: int) -> Court
  - get_schedule_blocks(court: Court, weekday: int) -> QuerySet[ScheduleBlock]
  - get_availability_grid(court: Court, date: date) -> list[dict]
    (cálculo de grilla de disponibilidad para el frontend)
"""
