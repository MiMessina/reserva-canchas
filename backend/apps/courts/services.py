"""
Service layer — app courts

Sprint 0: placeholder.

Toda lógica de negocio de canchas y horarios vive aquí (RULES.md).
Nunca en views ni serializers.

Expansión Sprint 1+:
  - create_court(*, name, court_type, surface, base_price, slot_duration_minutes, created_by) -> Court
  - update_court(*, court, **fields, updated_by) -> Court
  - deactivate_court(*, court, deactivated_by) -> Court  [soft-delete]
  - create_schedule_block(*, court, weekday, open_time, close_time) -> ScheduleBlock
  - get_available_slots(*, court, date) -> list[datetime]
    (selector de disponibilidad para la grilla pública)
"""
