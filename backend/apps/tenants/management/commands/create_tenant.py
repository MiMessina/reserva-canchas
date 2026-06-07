"""
Management command: create_tenant

Crea un complejo (tenant) con su esquema PostgreSQL, su dominio, ejecuta las
migraciones del esquema y crea el usuario tenant_admin inicial.

Uso (ejemplo de desarrollo — NO hardcodear la contraseña en scripts):
    python manage.py create_tenant \\
        --schema demo \\
        --name "Complejo Demo" \\
        --domain demo.localhost \\
        --admin-email admin@demo.localhost \\
        --admin-password "${DEMO_ADMIN_PASSWORD}"

    En entornos Docker la contraseña se lee de DEMO_ADMIN_PASSWORD (variable de
    entorno definida en .env). NUNCA pasar la contraseña como literal en scripts
    de producción o en control de versiones (ver RULES.md §2 y entrypoint.sh).

ADR-009: El alta de tenant en el MVP se hace por management command.
ADR-007: El User (incluido el tenant_admin) vive en el esquema del tenant.
FIX R-01: --admin-password es un parámetro de shell; la contraseña real proviene
           de la variable de entorno DEMO_ADMIN_PASSWORD (no de un valor hardcodeado).

Idempotencia:
    Si el schema_name ya existe, el comando avisa y sale sin error (no lanza
    excepción), para que los scripts de arranque puedan llamarlo sin romper.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from apps.tenants.models import Domain, Tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Crea un nuevo tenant (complejo deportivo) con su schema, dominio y admin inicial."

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

    def handle(self, *args, **options):
        schema_name = options["schema"].lower().strip()
        name = options["name"].strip()
        domain_name = options["domain"].lower().strip()
        admin_email = options["admin_email"].strip()
        admin_password = options["admin_password"]

        # Validaciones básicas de entrada
        if not schema_name.isidentifier():
            raise CommandError(
                f"El schema '{schema_name}' no es un identificador válido. "
                "Usá solo letras, números y guiones bajos."
            )

        # --- Idempotencia: verificar si el tenant ya existe ---
        if Tenant.objects.filter(schema_name=schema_name).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"[create_tenant] El tenant con schema '{schema_name}' ya existe. "
                    "No se realizaron cambios."
                )
            )
            return

        self.stdout.write(f"Creando tenant '{name}' (schema: {schema_name})...")

        # --- 1. Crear el Tenant (django-tenants crea el esquema automáticamente) ---
        try:
            tenant = Tenant(schema_name=schema_name, name=name)
            tenant.save()  # auto_create_schema=True: crea el esquema al guardar
        except Exception as exc:
            raise CommandError(f"Error al crear el tenant: {exc}") from exc

        self.stdout.write(f"  Esquema PostgreSQL '{schema_name}' creado.")

        # --- 2. Crear el Domain ---
        try:
            # Verificar si el dominio ya está en uso por otro tenant
            if Domain.objects.filter(domain=domain_name).exists():
                tenant.delete()
                raise CommandError(
                    f"El dominio '{domain_name}' ya está registrado en otro tenant. "
                    "Usá un dominio diferente."
                )

            Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=True,
            )
        except CommandError:
            raise
        except Exception as exc:
            tenant.delete()
            raise CommandError(f"Error al crear el dominio: {exc}") from exc

        self.stdout.write(f"  Dominio '{domain_name}' registrado.")

        # --- 3. Ejecutar migraciones del esquema del tenant ---
        self.stdout.write(f"  Ejecutando migraciones en el esquema '{schema_name}'...")
        try:
            from django.core.management import call_command
            call_command(
                "migrate_schemas",
                schema_name=schema_name,
                interactive=False,
                verbosity=0,
            )
        except Exception as exc:
            raise CommandError(f"Error al migrar el esquema '{schema_name}': {exc}") from exc

        self.stdout.write(f"  Migraciones del esquema '{schema_name}' completadas.")

        # --- 4. Crear el usuario tenant_admin dentro del esquema ---
        self.stdout.write(f"  Creando usuario tenant_admin ({admin_email})...")
        try:
            with schema_context(schema_name):
                User = get_user_model()

                if User.objects.filter(email=admin_email).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"  El usuario '{admin_email}' ya existe en el esquema. "
                            "No se creó uno nuevo."
                        )
                    )
                else:
                    # FIX R-08: User.USERNAME_FIELD = "email"; no existe campo username.
                    # create_user recibe email como primer argumento posicional.
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
                f"Error al crear el usuario tenant_admin: {exc}. "
                "El tenant y el esquema ya existen; podés crear el usuario manualmente "
                f"con: python manage.py shell (dentro del esquema '{schema_name}')."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTenant '{name}' creado exitosamente.\n"
                f"  Schema:  {schema_name}\n"
                f"  Dominio: {domain_name}\n"
                f"  Admin:   {admin_email}\n"
                f"\nPara acceder: configurá el host '{domain_name}' en /etc/hosts "
                "apuntando a 127.0.0.1 (en desarrollo local)."
            )
        )
