"""
AppConfig — apps.common

App utilitaria que provee el modelo base abstracto TimeStampedSoftDeleteModel.
No genera tablas propias (todos sus modelos son abstractos).

ADR-011: modelo base abstracto centraliza is_active (soft-delete), created_at y
updated_at para todas las entidades de negocio (Court, ScheduleBlock, Booking,
CashMovement). User queda excluido intencionalmente (su soft-delete proviene de
AbstractBaseUser.is_active).
"""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Utilidades comunes"
