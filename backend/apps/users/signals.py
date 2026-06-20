"""
Signals de la app users.

Sprint 14 — Login Centralizado:
  post_save de User → sincroniza UserEmailIndex en el schema public.
  Permite que el endpoint lookup-email encuentre en qué tenant existe un email.

Reglas:
  - La señal solo actúa cuando el schema activo NO es public.
  - UserEmailIndex usa update_or_create: es idempotente y soporta cambios de email.
  - No falla silenciosamente: los errores se loguean.
"""

import logging

from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.utils import get_public_schema_name

from apps.users.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def sync_user_email_index(sender, instance, **kwargs):
    """
    Mantiene UserEmailIndex actualizado en schema public cuando se crea/actualiza
    un User en el esquema tenant activo.

    IMPORTANTE: UserEmailIndex vive en el schema public (SHARED_APPS).
    La escritura debe hacerse con schema_context(public_schema) aunque el signal
    se dispare dentro de un schema de tenant.

    Se ignora si:
      - El schema activo es public (no hay usuarios de negocio en public).
      - El import de UserEmailIndex falla (ej: migraciones pendientes).
    """
    from django_tenants.utils import schema_context

    schema = connection.schema_name
    public_schema = get_public_schema_name()

    if schema == public_schema:
        return

    try:
        from apps.tenants.models import UserEmailIndex
        # Escribir en el schema public explícitamente
        with schema_context(public_schema):
            UserEmailIndex.objects.update_or_create(
                email=instance.email,
                schema_name=schema,
            )
    except Exception as exc:
        logger.warning(
            "[sync_user_email_index] No se pudo actualizar UserEmailIndex "
            "para email=%s schema=%s: %s",
            instance.email,
            schema,
            exc,
        )
