"""
Management command: init_platform_admin

Crea (o actualiza) el PlatformAdmin del Panel de System Admin (ADR-013).
PlatformAdmin vive en el esquema `public` (apps.tenants es SHARED_APPS).

Idempotente: si ya existe un PlatformAdmin con ese email, actualiza la contrasena.
Si no existe, lo crea.

Uso (ejemplo de desarrollo):
    python manage.py init_platform_admin \\
        --email admin@platform.localhost \\
        --password "${PLATFORM_ADMIN_PASSWORD}"

En Docker, el entrypoint llama este comando con las variables de entorno
PLATFORM_ADMIN_EMAIL y PLATFORM_ADMIN_PASSWORD definidas en .env.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import PlatformAdmin

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Crea o actualiza el PlatformAdmin del Panel de System Admin (esquema public)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Email del admin de platform. Ej: 'admin@platform.localhost'.",
        )
        parser.add_argument(
            "--password",
            required=True,
            help="Contrasena del admin de platform.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()
        password = options["password"]

        if not email or not password:
            raise CommandError("--email y --password son obligatorios.")

        try:
            existing = PlatformAdmin.objects.filter(email=email).first()
            if existing:
                existing.set_password(password)
                existing.is_active = True
                existing.save(update_fields=["password", "is_active", "updated_at"])
                self.stdout.write(
                    self.style.WARNING(
                        f"[init_platform_admin] PlatformAdmin '{email}' ya existia. "
                        "Contrasena actualizada."
                    )
                )
            else:
                admin = PlatformAdmin(email=email, is_active=True)
                admin.set_password(password)
                admin.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[init_platform_admin] PlatformAdmin '{email}' creado exitosamente."
                    )
                )
        except Exception as exc:
            raise CommandError(
                f"Error al crear/actualizar el PlatformAdmin: {exc}"
            ) from exc
