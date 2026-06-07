"""
Modelos — app courts

Sprint 0: VACÍO intencionalmente.

Los modelos Court y ScheduleBlock se construyen en Sprint 1+.
Ver docs/DER.md para la especificación completa.

Court:
  - name, court_type (FUTBOL_5|FUTBOL_7|PADEL), surface
  - base_price (decimal), slot_duration_minutes (int)
  - is_active, created_at, updated_at

ScheduleBlock:
  - court (FK), weekday (0-6), open_time, close_time
  - is_active, created_at, updated_at
"""
