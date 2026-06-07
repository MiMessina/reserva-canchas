"""
Selectors (queries de lectura) — app courts

Los selectors encapsulan queries de lectura complejas, separando la lógica
de consulta de las views (ARCHITECTURE.md §4).

Sprint 1: las queries simples se hacen directamente en get_queryset() de las views
(CourtViewSet, ScheduleBlockViewSet). Los selectors más complejos se agregan aquí.

Sprint 2+:
  - get_active_courts() -> QuerySet[Court]
  - get_court_by_id(court_id: int) -> Court
  - get_schedule_blocks(court: Court, weekday: int) -> QuerySet[ScheduleBlock]
  - get_availability_grid(court: Court, date: date) -> list[dict]
    (cálculo de grilla de disponibilidad para la grilla pública — Sprint 2)
"""
