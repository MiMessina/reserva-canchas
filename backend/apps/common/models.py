"""
Modelo base abstracto — apps.common

ADR-011: Centraliza los tres campos obligatorios de toda entidad de negocio:
  - is_active    → soft-delete (prohibido DELETE físico, ver RULES.md §4)
  - created_at   → timestamp de creación en UTC (USE_TZ=True en settings)
  - updated_at   → timestamp de última modificación en UTC

Uso:
    class Court(TimeStampedSoftDeleteModel):
        ...

Este módulo NO genera tablas (abstract = True en Meta).
"""

from django.db import models


class TimeStampedSoftDeleteModel(models.Model):
    """
    Clase base abstracta para todas las entidades de negocio.

    Garantiza soft-delete y timestamps UTC consistentes en todo el dominio.
    Los modelos que hereden de esta clase obtienen automáticamente:

      is_active (bool, default=True)
        Indicador de estado activo. Poner en False equivale a una baja lógica.
        Prohibido DELETE físico (RULES.md §4).

      created_at (DateTimeField, auto_now_add=True)
        Fecha/hora de creación. Solo se escribe una vez, en UTC.

      updated_at (DateTimeField, auto_now=True)
        Fecha/hora de la última modificación. Se actualiza automáticamente, en UTC.
    """

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Desmarcar en lugar de borrar (soft-delete).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        abstract = True
