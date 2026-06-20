"""
Management command: sync_email_index

Recorre todos los tenants activos y puebla UserEmailIndex (schema public)
con los emails de los usuarios existentes en cada tenant.

Es idempotente (usa update_or_create) y seguro de correr en cualquier momento.
Se llama automáticamente desde entrypoint.sh al arrancar el backend.

Cubre el caso de usuarios pre-existentes (creados antes del Sprint 14)
que no tienen entrada en UserEmailIndex porque la señal post_save
solo indexa usuarios creados a partir de la instalación del Sprint 14.

Uso:
    python manage.py sync_email_index
"""

import logging

from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import Tenant, UserEmailIndex

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sincroniza UserEmailIndex (schema public) con los usuarios de todos los tenants activos."

    def handle(self, *args, **options):
        public_schema = get_public_schema_name()
        tenants = Tenant.objects.filter(is_active=True)
        total_indexed = 0

        for tenant in tenants:
            schema = tenant.schema_name
            if schema == public_schema:
                continue

            try:
                with schema_context(schema):
                    from apps.users.models import User
                    emails = list(User.objects.values_list("email", flat=True))

                count = 0
                with schema_context(public_schema):
                    for email in emails:
                        UserEmailIndex.objects.update_or_create(
                            email=email,
                            schema_name=schema,
                        )
                        count += 1

                total_indexed += count
                self.stdout.write(f"  {schema}: {count} usuario(s) indexado(s).")

            except Exception as exc:
                logger.warning("[sync_email_index] Error en schema %s: %s", schema, exc)
                self.stdout.write(
                    self.style.WARNING(f"  {schema}: error al sincronizar — {exc}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"[sync_email_index] Completado. {total_indexed} email(s) indexado(s) en total."
            )
        )
