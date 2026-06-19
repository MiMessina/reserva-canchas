"""
Management command: init_tenant

Crea un complejo (tenant) con su esquema PostgreSQL, su dominio, ejecuta las
migraciones del esquema y crea el usuario tenant_admin inicial.

Nombre: `init_tenant` (no `create_tenant`) para evitar colisión con el
comando built-in de `django-tenants` que tiene el mismo nombre pero diferente
interfaz de argumentos. Django carga commands en orden FIFO de INSTALLED_APPS
(el primero gana), por lo que django_tenants siempre ganaría sobre apps.tenants.

Uso (ejemplo de desarrollo — NO hardcodear la contraseña en scripts):
    python manage.py init_tenant \\
        --schema demo \\
        --name "Complejo Demo" \\
        --domain demo.localhost \\
        --admin-email admin@demo.localhost \\
        --admin-password "${DEMO_ADMIN_PASSWORD}"

    En entornos Docker la contraseña se lee de DEMO_ADMIN_PASSWORD (variable de
    entorno definida en .env). NUNCA pasar la contraseña como literal en scripts
    de producción o en control de versiones (ver RULES.md §2 y entrypoint.sh).

ADR-009: El alta de tenant en el MVP se hace por management command.
ADR-013: La lógica de creación se extrajo a tenants/services.py para que el
         Panel de System Admin la reutilice via API REST.
ADR-007: El User (incluido el tenant_admin) vive en el esquema del tenant.
FIX R-01: --admin-password es un parámetro de shell; la contraseña real proviene
           de la variable de entorno DEMO_ADMIN_PASSWORD (no de un valor hardcodeado).

Idempotencia:
    Si el schema_name ya existe, el comando avisa y sale sin error (no lanza
    excepción), para que los scripts de arranque puedan llamarlo sin romper.
    Si el tenant existe pero el admin no, lo crea/actualiza (upsert).
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from apps.tenants.models import Tenant
from apps.tenants.services import (
    DomainAlreadyExists,
    InvalidSchemaName,
    SchemaAlreadyExists,
    TenantCreationFailed,
    create_tenant_service,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Inicializa un nuevo tenant (complejo deportivo) con su schema, dominio y admin inicial."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            required=True,
            help="Nombre del esquema PostgreSQL (lowercase, sin espacios). Ej: 'demo'.",
        )
        parser.add_argument(
            "--name",
            required=True,
            help="Nombre del complejo. Ej: 'Complejo Los Pinos'.",
        )
        parser.add_argument(
            "--domain",
            required=True,
            help="Dominio/subdominio que apunta al tenant. Ej: 'demo.localhost'.",
        )
        parser.add_argument(
            "--admin-email",
            required=True,
            help="Email del usuario tenant_admin inicial.",
        )
        parser.add_argument(
            "--admin-password",
            required=True,
            help="Contraseña del usuario tenant_admin inicial.",
        )

    def _upsert_admin(self, schema_name: str, admin_email: str, admin_password: str) -> None:
        """
        Crea el usuario tenant_admin si no existe, o actualiza su contraseña y rol
        si ya existe. Esto hace al comando verdaderamente idempotente: cada arranque
        del contenedor sincroniza la contraseña con DEMO_ADMIN_PASSWORD del .env.
        """
        self.stdout.write(f"  Verificando usuario tenant_admin ({admin_email})...")
        try:
            with schema_context(schema_name):
                User = get_user_model()
                existing = User.objects.filter(email=admin_email).first()
                if existing:
                    existing.set_password(admin_password)
                    existing.role = "tenant_admin"
                    existing.is_staff = True
                    existing.save(update_fields=["password", "role", "is_staff"])
                    self.stdout.write(
                        self.style.WARNING(
                            f"  El usuario '{admin_email}' ya existía. "
                            "Contraseña y rol actualizados."
                        )
                    )
                else:
                    # FIX R-08: User.USERNAME_FIELD = "email"; no existe campo username.
                    user = User.objects.create_user(
                        email=admin_email,
                        password=admin_password,
                        role="tenant_admin",
                        is_staff=True,
                    )
                    self.stdout.write(
                        f"  Usuario tenant_admin creado: {user.email} (id={user.pk})."
                    )
        except Exception as exc:
            raise CommandError(
                f"Error al crear/actualizar el usuario tenant_admin: {exc}. "
                "El tenant y el esquema ya existen; podés crear el usuario manualmente "
                f"con: python manage.py shell (dentro del esquema '{schema_name}')."
            ) from exc

    def handle(self, *args, **options):
        schema_name = options["schema"].lower().strip()
        name = options["name"].strip()
        domain_name = options["domain"].lower().strip()
        admin_email = options["admin_email"].strip()
        admin_password = options["admin_password"]

        # --- Idempotencia: si el tenant ya existe, solo actualizar el admin ---
        tenant_qs = Tenant.objects.filter(schema_name=schema_name)
        if tenant_qs.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"[init_tenant] El tenant con schema '{schema_name}' ya existe."
                )
            )
            self._upsert_admin(schema_name, admin_email, admin_password)
            return

        self.stdout.write(f"Creando tenant '{name}' (schema: {schema_name})...")

        # Delegar al service (ADR-013: lógica centralizada en services.py)
        try:
            tenant = create_tenant_service(
                name=name,
                schema_name=schema_name,
                domain=domain_name,
                admin_email=admin_email,
                admin_password=admin_password,
            )
        except (InvalidSchemaName, SchemaAlreadyExists, DomainAlreadyExists, TenantCreationFailed) as exc:
            raise CommandError(exc.message) from exc
        except Exception as exc:
            raise CommandError(f"Error inesperado al crear el tenant: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTenant '{tenant.name}' creado exitosamente.\n"
                f"  Schema:  {schema_name}\n"
                f"  Dominio: {domain_name}\n"
                f"  Admin:   {admin_email}\n"
                f"\nPara acceder: configurá el host '{domain_name}' en /etc/hosts "
                "apuntando a 127.0.0.1 (en desarrollo local)."
            )
        )
