"""
Modelos — app courts

Entidades del dominio de canchas y horarios.

ADR-006: Duración del turno configurable por cancha (Court.slot_duration_minutes).
         Detección de overbooking por solapamiento de intervalos [start_dt, end_dt).
ADR-011: Court y ScheduleBlock heredan de TimeStampedSoftDeleteModel (is_active,
         created_at, updated_at).

Reglas de datos (RULES.md §4, DER.md):
  - Soft-delete obligatorio via is_active (heredado). Prohibido DELETE físico.
  - Fechas/horas en UTC (USE_TZ=True en settings).
  - Toda entidad tiene created_at y updated_at (heredados).
  - name en Court es único dentro del esquema tenant (cada esquema está aislado).
  - ScheduleBlock referencia Court con PROTECT (no se puede borrar una cancha con bloques).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedSoftDeleteModel


class Court(TimeStampedSoftDeleteModel):
    """
    Cancha deportiva del complejo.

    Representa un espacio alquilable. El tipo puede ser Fútbol 5, Fútbol 7 o Pádel.
    La duración del turno (slot_duration_minutes) define cuánto dura cada reserva;
    combinada con start_dt genera end_dt en el motor de reservas (ADR-006).

    El campo name es único dentro del tenant (cada complejo tiene su propio esquema
    PostgreSQL aislado, por lo que la restricción unique opera por esquema).
    """

    class CourtType(models.TextChoices):
        FUTBOL_5 = "futbol_5", "Fútbol 5"
        FUTBOL_7 = "futbol_7", "Fútbol 7"
        PADEL = "padel", "Pádel"

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre",
        help_text="Identificador único de la cancha dentro del complejo.",
    )
    court_type = models.CharField(
        max_length=20,
        choices=CourtType.choices,
        verbose_name="Tipo de cancha",
        help_text="Categoría deportiva: fútbol 5, fútbol 7 o pádel.",
    )
    surface = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Superficie",
        help_text="Tipo de superficie (ej: césped sintético, cemento, moqueta).",
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Precio base",
        help_text="Precio del turno en pesos. Debe ser mayor o igual a 0.",
    )
    slot_duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Duración del turno (minutos)",
        help_text=(
            "Duración en minutos de cada turno reservable. "
            "Determina end_dt = start_dt + slot_duration_minutes (ADR-006)."
        ),
    )

    class Meta:
        verbose_name = "Cancha"
        verbose_name_plural = "Canchas"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_court_type_display()})"


class ScheduleBlock(TimeStampedSoftDeleteModel):
    """
    Bloque horario de disponibilidad de una cancha.

    Define el intervalo [open_time, close_time) en el que una cancha está
    disponible para ser reservada en un día de la semana específico.

    Convención de weekday (igual que date.weekday() de Python):
      0 = lunes, 1 = martes, ..., 6 = domingo

    Una cancha puede tener múltiples bloques por día (turno partido), siempre
    que no se superpongan. La validación de solapamiento vive en services.py.

    La FK a Court usa PROTECT (no se puede borrar una cancha que tiene bloques
    de horario asociados, activos o no).
    """

    class Weekday(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    court = models.ForeignKey(
        Court,
        on_delete=models.PROTECT,
        related_name="schedule_blocks",
        verbose_name="Cancha",
        help_text="Cancha a la que pertenece este bloque horario.",
    )
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        verbose_name="Día de la semana",
        help_text="Día al que aplica este bloque (0=lunes … 6=domingo, igual que Python date.weekday()).",
    )
    open_time = models.TimeField(
        verbose_name="Hora de apertura",
        help_text="Hora de inicio de disponibilidad de la cancha.",
    )
    close_time = models.TimeField(
        verbose_name="Hora de cierre",
        help_text="Hora de fin de disponibilidad de la cancha. Debe ser mayor que open_time.",
    )

    class Meta:
        verbose_name = "Bloque de horario"
        verbose_name_plural = "Bloques de horario"
        ordering = ["court", "weekday", "open_time"]

    def __str__(self):
        return (
            f"{self.court.name} — "
            f"{self.get_weekday_display()} "
            f"{self.open_time.strftime('%H:%M')}–{self.close_time.strftime('%H:%M')}"
        )
