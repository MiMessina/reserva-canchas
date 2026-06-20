"""
Service layer — app tenants.

Lógica de negocio para:
  - Configuración del complejo (ComplexSettings).
  - Creación de tenants (create_tenant_service) — refactor de ADR-009 para ADR-013.

La creación de tenants se extrae aquí desde el management command para que el
Panel de System Admin (views_platform.py) pueda reutilizarla via API REST.

Regla: toda lógica de negocio vive en services.py, nunca en views ni serializers.
"""

import logging
import re

from apps.tenants.models import ComplexSettings, Domain, Tenant

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepciones del dominio de tenants (ADR-013)
# ---------------------------------------------------------------------------

class TenantServiceError(Exception):
    """Base para errores del service de tenants. Lleva un código de negocio."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class SchemaAlreadyExists(TenantServiceError):
    def __init__(self, schema_name: str):
        super().__init__(
            code="SCHEMA_ALREADY_EXISTS",
            message=f"El schema '{schema_name}' ya existe.",
        )


class DomainAlreadyExists(TenantServiceError):
    def __init__(self, domain: str):
        super().__init__(
            code="DOMAIN_ALREADY_EXISTS",
            message=f"El dominio '{domain}' ya está en uso.",
        )


class InvalidSchemaName(TenantServiceError):
    def __init__(self, schema_name: str):
        super().__init__(
            code="INVALID_SCHEMA_NAME",
            message=(
                f"El schema_name '{schema_name}' es inválido. "
                "Solo puede contener letras minúsculas, números y guion bajo, "
                "debe empezar con letra y tener máximo 63 caracteres. "
                "No puede ser un nombre reservado de PostgreSQL."
            ),
        )


class TenantCreationFailed(TenantServiceError):
    def __init__(self, message: str = "Error al crear el tenant. El proceso fue revertido."):
        super().__init__(
            code="TENANT_CREATION_FAILED",
            message=message,
        )


# ---------------------------------------------------------------------------
# Nombres reservados de PostgreSQL / django-tenants (no permitidos como schema)
# ---------------------------------------------------------------------------
_RESERVED_SCHEMA_NAMES = frozenset({
    "public",
    "information_schema",
    "pg_catalog",
    "pg_toast",
    "pg_temp",
    "pg_internal",
    "test",           # usado por TenantTestCase de django-tenants
})


_SCHEMA_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')


def _validate_schema_name(schema_name: str) -> None:
    """
    Valida que el schema_name cumpla las reglas del negocio (ADR-013):
      - Solo [a-z][a-z0-9_]*
      - Máximo 63 caracteres
      - No puede ser un nombre reservado de PostgreSQL ni de django-tenants

    Lanza InvalidSchemaName si no pasa la validación.
    """
    pattern = _SCHEMA_NAME_PATTERN
    if (
        not schema_name
        or len(schema_name) > 63
        or not pattern.match(schema_name)
        or schema_name in _RESERVED_SCHEMA_NAMES
        or schema_name.startswith("pg_")
    ):
        raise InvalidSchemaName(schema_name)


def create_tenant_service(
    *,
    name: str,
    schema_name: str,
    domain: str,
    admin_email: str,
    admin_password: str,
    bot_mode: str = "production",
) -> Tenant:
    """
    Crea un tenant completo: Tenant + Domain + migraciones del esquema + tenant_admin.

    Flujo (ADR-013, refactor de ADR-009):
      1. Validar schema_name (formato + reservados).
      2. Verificar unicidad de schema_name y domain.
      3. Crear Tenant (django-tenants crea el esquema al guardar).
      4. Crear Domain primario.
      5. Ejecutar migrate_schemas para el nuevo esquema.
      6. Crear usuario tenant_admin dentro del esquema.

    Manejo de errores:
      - Si falla tras crear el Tenant, intenta borrarlo (rollback parcial).
      - Las excepciones de dominio (TenantServiceError) se propagan al llamador.
      - Los errores inesperados se envuelven en TenantCreationFailed.

    Nota: migrate_schemas es sincrónico y puede tardar varios segundos.
    Para el MVP esto es aceptable (ADR-013 §Consecuencias).

    Args:
        name: Nombre del complejo (ej: "Complejo Los Pinos").
        schema_name: Schema PostgreSQL (ej: "lospinos"). Inmutable tras la creación.
        domain: Dominio primario (ej: "lospinos.canchero.com").
        admin_email: Email del tenant_admin inicial.
        admin_password: Contraseña del tenant_admin inicial.

    Returns:
        Tenant creado y activo.

    Raises:
        InvalidSchemaName: schema_name inválido.
        SchemaAlreadyExists: schema_name ya está en uso.
        DomainAlreadyExists: domain ya está en uso.
        TenantCreationFailed: cualquier otro error durante la creación.
    """
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django_tenants.utils import schema_context

    schema_name = schema_name.lower().strip()
    domain = domain.lower().strip()
    admin_email = admin_email.strip()

    # 1. Validar formato del schema_name
    _validate_schema_name(schema_name)

    # 2. Verificar unicidad
    if Tenant.objects.filter(schema_name=schema_name).exists():
        raise SchemaAlreadyExists(schema_name)

    if Domain.objects.filter(domain=domain).exists():
        raise DomainAlreadyExists(domain)

    tenant = None

    # 3. Crear Tenant (django-tenants crea el esquema PG al hacer .save())
    try:
        tenant = Tenant(schema_name=schema_name, name=name, bot_mode=bot_mode)
        tenant.save()
        logger.info("[create_tenant_service] Esquema '%s' creado.", schema_name)
    except Exception as exc:
        logger.error("Tenant creation failed: %s", exc, exc_info=True)
        raise TenantCreationFailed("Error al crear el tenant. El proceso fue revertido.") from exc

    # A partir de aquí, si falla algo intentamos revertir el tenant
    try:
        # 4. Crear Domain
        Domain.objects.create(domain=domain, tenant=tenant, is_primary=True)
        logger.info("[create_tenant_service] Dominio '%s' registrado.", domain)

        # 5. Ejecutar migraciones del nuevo esquema
        call_command(
            "migrate_schemas",
            schema_name=schema_name,
            interactive=False,
            verbosity=0,
        )
        logger.info("[create_tenant_service] Migraciones de '%s' completadas.", schema_name)

        # 6. Crear tenant_admin dentro del esquema
        with schema_context(schema_name):
            User = get_user_model()
            if not User.objects.filter(email=admin_email).exists():
                User.objects.create_user(
                    email=admin_email,
                    password=admin_password,
                    role="tenant_admin",
                    is_staff=True,
                )
                logger.info(
                    "[create_tenant_service] tenant_admin '%s' creado en esquema '%s'.",
                    admin_email,
                    schema_name,
                )

        # 7. Seed de conversaciones demo si el tenant nace en modo mock
        if bot_mode == "mock":
            from apps.agent.services import seed_demo_conversations
            seed_demo_conversations(schema_name)
            logger.info(
                "[create_tenant_service] Seed demo insertado en esquema '%s'.", schema_name
            )

    except Exception as exc:
        logger.error(
            "[create_tenant_service] Error tras crear el tenant, intentando rollback: %s",
            exc,
        )
        try:
            tenant.delete(force_drop=True)
        except Exception as rollback_exc:
            logger.error(
                "[create_tenant_service] Fallo en rollback del tenant '%s': %s",
                schema_name,
                rollback_exc,
            )
        logger.error("Tenant creation failed: %s", exc, exc_info=True)
        raise TenantCreationFailed("Error al crear el tenant. El proceso fue revertido.") from exc

    return tenant


# ---------------------------------------------------------------------------
# Sprint 14 — Login Centralizado
# ---------------------------------------------------------------------------

def lookup_email(email: str) -> list:
    """
    Retorna lista de tenants donde existe el email.
    Corre en schema public (UserEmailIndex está ahí).

    Returns:
        Lista de dicts con schema_name, tenant_name, domain.
    """
    from apps.tenants.models import UserEmailIndex

    entries = UserEmailIndex.objects.filter(email=email)
    result = []
    for entry in entries:
        try:
            tenant = Tenant.objects.get(schema_name=entry.schema_name, is_active=True)
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            result.append({
                "schema_name": entry.schema_name,
                "tenant_name": tenant.name,
                "domain": domain.domain if domain else entry.schema_name,
            })
        except Tenant.DoesNotExist:
            pass
    return result


def central_login(email: str, password: str, schema_name: str) -> dict:
    """
    Autentica el user en el esquema dado y genera un OneTimeCode.

    Returns:
        {"code": ..., "redirect_url": ...}

    Raises:
        ValueError con código de negocio:
            TENANT_INACTIVE, INVALID_CREDENTIALS, ROLE_NOT_ALLOWED
    """
    import secrets
    from datetime import timedelta
    from django.utils import timezone
    from django_tenants.utils import schema_context
    from apps.tenants.models import OneTimeCode

    # Verificar tenant activo
    try:
        tenant = Tenant.objects.get(schema_name=schema_name, is_active=True)
    except Tenant.DoesNotExist:
        raise ValueError("TENANT_INACTIVE")

    user_id = None
    with schema_context(schema_name):
        from apps.users.models import User as TenantUser
        try:
            user_obj = TenantUser.objects.get(email=email)
        except TenantUser.DoesNotExist:
            raise ValueError("INVALID_CREDENTIALS")

        if not user_obj.check_password(password):
            raise ValueError("INVALID_CREDENTIALS")

        if not user_obj.is_active:
            raise ValueError("INVALID_CREDENTIALS")

        # Solo tenant_admin y operator pueden usar el login centralizado
        if user_obj.role not in ("tenant_admin", "operator"):
            raise ValueError("ROLE_NOT_ALLOWED")

        user_id = user_obj.pk

    # Generar código OTC (en schema public)
    code = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(seconds=60)
    OneTimeCode.objects.create(
        code=code,
        schema_name=schema_name,
        user_id=user_id,
        expires_at=expires_at,
    )

    domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
    domain_str = domain.domain if domain else f"{schema_name}.localhost"
    redirect_url = f"http://{domain_str}"

    return {"code": code, "redirect_url": redirect_url}


def exchange_code(code: str) -> dict:
    """
    Intercambia el OneTimeCode por un par JWT (access + refresh).
    Marca el código como usado.

    Returns:
        {"access": ..., "refresh": ...}

    Raises:
        ValueError con código de negocio:
            CODE_NOT_FOUND, CODE_ALREADY_USED, CODE_EXPIRED
    """
    from django.utils import timezone
    from django_tenants.utils import schema_context
    from rest_framework_simplejwt.tokens import RefreshToken
    from apps.tenants.models import OneTimeCode

    try:
        otc = OneTimeCode.objects.get(code=code)
    except OneTimeCode.DoesNotExist:
        raise ValueError("CODE_NOT_FOUND")

    if otc.used:
        raise ValueError("CODE_ALREADY_USED")

    if timezone.now() > otc.expires_at:
        raise ValueError("CODE_EXPIRED")

    otc.used = True
    otc.save(update_fields=["used"])

    with schema_context(otc.schema_name):
        from apps.users.models import User as TenantUser
        user = TenantUser.objects.get(pk=otc.user_id)
        refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def get_complex_settings() -> ComplexSettings:
    """
    Retorna la configuración del complejo activo (tenant actual).

    Usa get_or_create con complex_name vacío como default: siempre retorna
    una instancia válida, nunca lanza 404. El tenant activo lo determina
    el esquema de la conexión activa (middleware de django-tenants).

    Returns:
        ComplexSettings: instancia de configuración del complejo.
    """
    settings_obj, _ = ComplexSettings.objects.get_or_create(
        defaults={"complex_name": ""}
    )
    return settings_obj


def update_complex_settings(*, data: dict) -> ComplexSettings:
    """
    Actualiza los campos de la configuración del complejo activo.

    Semántica PATCH: solo actualiza los campos presentes en `data`.
    Los campos ausentes no se modifican. Si la configuración no existe
    la crea antes de actualizar.

    Args:
        data: dict con los campos a actualizar (subset de ComplexSettings).

    Returns:
        ComplexSettings: instancia actualizada.
    """
    settings_obj = get_complex_settings()

    for field, value in data.items():
        setattr(settings_obj, field, value)

    settings_obj.save()
    return settings_obj
