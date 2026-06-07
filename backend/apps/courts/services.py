"""
Service layer — app courts

Toda la lógica de negocio de canchas y horarios vive aquí (RULES.md §4, ARCHITECTURE.md §4).
Prohibido duplicar estas reglas en views ni serializers.

Funciones exportadas:
  create_court(*, name, court_type, surface, base_price, slot_duration_minutes) -> Court
  update_court(*, court, **fields) -> Court
  deactivate_court(*, court) -> Court          [soft-delete: is_active=False]

  create_schedule_block(*, court, weekday, open_time, close_time) -> ScheduleBlock
  update_schedule_block(*, schedule_block, **fields) -> ScheduleBlock
  deactivate_schedule_block(*, schedule_block) -> ScheduleBlock  [soft-delete]

Validaciones de negocio (lanzadas como DRF ValidationError con código de negocio):
  INVALID_SCHEDULE  — open_time >= close_time
  SCHEDULE_OVERLAP  — el bloque nuevo se solapa con un bloque activo existente en la
                      misma cancha y el mismo día de la semana.

Códigos de negocio (API_GUIDELINES.md §7):
  INVALID_SCHEDULE, SCHEDULE_OVERLAP

Nota sobre solapamiento:
  Solapamiento se detecta cuando:
    nuevo.open_time < existente.close_time  AND  nuevo.close_time > existente.open_time
  Esto cubre parcial izquierdo, parcial derecho, contenido y contenedor.
  Se excluye el propio id al editar (para no rechazar la propia fila existente).
"""

import logging

from rest_framework.exceptions import ValidationError

from apps.courts.models import Court, ScheduleBlock

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Court
# ---------------------------------------------------------------------------

def create_court(
    *,
    name: str,
    court_type: str,
    surface: str = "",
    base_price,
    slot_duration_minutes: int,
) -> Court:
    """
    Crea una nueva cancha activa.

    Parámetros:
      name                   — identificador único de la cancha en el tenant.
      court_type             — valor de Court.CourtType (futbol_5, futbol_7, padel).
      surface                — superficie (opcional).
      base_price             — precio base del turno (>= 0).
      slot_duration_minutes  — duración del turno en minutos (>= 1).

    Retorna la instancia Court creada.
    """
    court = Court.objects.create(
        name=name,
        court_type=court_type,
        surface=surface,
        base_price=base_price,
        slot_duration_minutes=slot_duration_minutes,
        is_active=True,
    )
    logger.info("Cancha creada: id=%s nombre=%s", court.pk, court.name)
    return court


def update_court(*, court: Court, **fields) -> Court:
    """
    Actualiza los campos indicados de una cancha existente.

    Solo se actualizan los campos presentes en `fields`. Los campos válidos
    son: name, court_type, surface, base_price, slot_duration_minutes.

    Retorna la instancia Court actualizada.
    """
    allowed_fields = {"name", "court_type", "surface", "base_price", "slot_duration_minutes"}
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(court, field, value)
    court.save()
    logger.info("Cancha actualizada: id=%s", court.pk)
    return court


def deactivate_court(*, court: Court) -> Court:
    """
    Baja lógica de una cancha (soft-delete: is_active=False).

    Prohibido DELETE físico (RULES.md §4). La cancha sigue existiendo en DB.

    Retorna la instancia Court con is_active=False.
    """
    court.is_active = False
    court.save(update_fields=["is_active", "updated_at"])
    logger.info("Cancha desactivada (soft-delete): id=%s", court.pk)
    return court


# ---------------------------------------------------------------------------
# ScheduleBlock
# ---------------------------------------------------------------------------

def _validate_schedule_block(
    *,
    open_time,
    close_time,
    court: Court,
    weekday: int,
    exclude_id: int | None = None,
) -> None:
    """
    Valida reglas de negocio para un bloque horario.

    Lanza ValidationError con el código de negocio correspondiente si:
      - open_time >= close_time (INVALID_SCHEDULE).
      - El bloque se solapa con un bloque activo existente en la misma cancha
        y el mismo día de la semana (SCHEDULE_OVERLAP).

    El parámetro exclude_id permite excluir el propio registro al editar,
    evitando que se auto-rechace por solapamiento consigo mismo.
    """
    # Regla 1: open_time debe ser estrictamente menor que close_time.
    # No se admiten rangos que crucen medianoche en el MVP.
    if open_time >= close_time:
        raise ValidationError(
            {
                "non_field_errors": [
                    {
                        "code": "INVALID_SCHEDULE",
                        "message": (
                            "La hora de apertura debe ser anterior a la hora de cierre. "
                            "No se admiten rangos que crucen medianoche."
                        ),
                    }
                ]
            }
        )

    # Regla 2: solapamiento con bloques activos en la misma cancha y día.
    # Solapamiento: nuevo.open < existente.close AND nuevo.close > existente.open
    qs = ScheduleBlock.objects.filter(
        court=court,
        weekday=weekday,
        is_active=True,
        open_time__lt=close_time,
        close_time__gt=open_time,
    )
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)

    if qs.exists():
        conflicting = qs.first()
        raise ValidationError(
            {
                "non_field_errors": [
                    {
                        "code": "SCHEDULE_OVERLAP",
                        "message": (
                            f"El bloque horario se solapa con uno existente "
                            f"({conflicting.open_time.strftime('%H:%M')}–"
                            f"{conflicting.close_time.strftime('%H:%M')} "
                            f"del {conflicting.get_weekday_display()})."
                        ),
                        "details": {
                            "conflicting_open": conflicting.open_time.strftime("%H:%M"),
                            "conflicting_close": conflicting.close_time.strftime("%H:%M"),
                        },
                    }
                ]
            }
        )


def create_schedule_block(
    *,
    court: Court,
    weekday: int,
    open_time,
    close_time,
) -> ScheduleBlock:
    """
    Crea un bloque horario activo para una cancha y día de la semana.

    Parámetros:
      court      — instancia Court activa.
      weekday    — día de la semana (0=lunes … 6=domingo, convención Python date.weekday()).
      open_time  — hora de apertura (time).
      close_time — hora de cierre (time). Debe ser mayor que open_time.

    Retorna la instancia ScheduleBlock creada.

    Lanza ValidationError con código INVALID_SCHEDULE o SCHEDULE_OVERLAP si corresponde.
    """
    _validate_schedule_block(
        open_time=open_time,
        close_time=close_time,
        court=court,
        weekday=weekday,
    )

    block = ScheduleBlock.objects.create(
        court=court,
        weekday=weekday,
        open_time=open_time,
        close_time=close_time,
        is_active=True,
    )
    logger.info(
        "Bloque horario creado: id=%s cancha=%s dia=%s %s-%s",
        block.pk, court.pk, weekday, open_time, close_time,
    )
    return block


def update_schedule_block(*, schedule_block: ScheduleBlock, **fields) -> ScheduleBlock:
    """
    Actualiza los campos indicados de un bloque horario.

    Campos válidos: weekday, open_time, close_time.
    Aplica validaciones de negocio (INVALID_SCHEDULE, SCHEDULE_OVERLAP)
    excluyendo el propio id para no auto-rechazarse.

    Retorna la instancia ScheduleBlock actualizada.
    """
    allowed_fields = {"weekday", "open_time", "close_time"}

    # Aplicar los cambios al objeto en memoria para validar con los valores combinados
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(schedule_block, field, value)

    _validate_schedule_block(
        open_time=schedule_block.open_time,
        close_time=schedule_block.close_time,
        court=schedule_block.court,
        weekday=schedule_block.weekday,
        exclude_id=schedule_block.pk,
    )

    schedule_block.save()
    logger.info("Bloque horario actualizado: id=%s", schedule_block.pk)
    return schedule_block


def deactivate_schedule_block(*, schedule_block: ScheduleBlock) -> ScheduleBlock:
    """
    Baja lógica de un bloque horario (soft-delete: is_active=False).

    Prohibido DELETE físico (RULES.md §4). El registro sigue en DB.

    Retorna la instancia ScheduleBlock con is_active=False.
    """
    schedule_block.is_active = False
    schedule_block.save(update_fields=["is_active", "updated_at"])
    logger.info("Bloque horario desactivado (soft-delete): id=%s", schedule_block.pk)
    return schedule_block
