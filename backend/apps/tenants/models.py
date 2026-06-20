"""
Modelos de la app tenants.

ADR-001: Multi-tenant por esquema PostgreSQL con django-tenants.
ADR-009: Alta de tenant por management command.

Modelos y sus esquemas:
- Tenant y Domain (SHARED_APPS): viven en el esquema `public`.
- ComplexSettings (TENANT_APPS): vive en el esquema de cada tenant.
  Contiene la configuración pública/operativa del complejo (nombre visible,
  datos de pago, contacto). El aislamiento por esquema garantiza una instancia
  por tenant sin necesidad de unique_together.

Reglas:
- Soft-delete con is_active; prohibido DELETE físico.
- Fechas/horas en UTC (USE_TZ=True).
"""

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from apps.common.models import TimeStampedSoftDeleteModel


class Tenant(TenantMixin):
    """
    Representa un complejo deportivo (cliente B2B del SaaS).

    Cada Tenant tiene su propio esquema PostgreSQL aislado.
    Los datos de negocio (canchas, reservas, caja, usuarios) viven
    dentro de ese esquema y son completamente inaccesibles desde otros.
    """

    class BotMode(models.TextChoices):
        MOCK = "mock", "Demo (conversaciones seed)"
        PRODUCTION = "production", "Producción (mensajes reales)"

    name = models.CharField(
        max_length=200,
        verbose_name="Nombre del complejo",
        help_text="Nombre del complejo deportivo (ej: 'Complejo Los Pinos').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Soft-delete: False deshabilita el complejo sin borrar datos.",
    )
    bot_mode = models.CharField(
        max_length=20,
        choices=BotMode.choices,
        default=BotMode.PRODUCTION,
        verbose_name="Modo del bot",
        help_text=(
            "mock: muestra conversaciones seed de demostración. "
            "production: muestra mensajes reales del bot WhatsApp."
        ),
    )

    # django-tenants usa esta flag para crear el esquema automáticamente
    auto_create_schema = True

    class Meta:
        verbose_name = "Complejo (Tenant)"
        verbose_name_plural = "Complejos (Tenants)"

    def __str__(self):
        return f"{self.name} ({self.schema_name})"


class Domain(DomainMixin):
    """
    Dominio o subdominio que identifica al tenant en cada request.

    django-tenants resuelve el tenant activo por el campo `domain` de esta entidad.
    Cada tenant puede tener múltiples dominios; uno debe ser el primario.

    Ejemplos:
        - localhost       → tenant public (admin de la plataforma)
        - demo.localhost  → tenant demo (complejo de prueba)
        - canchas.mi-complejo.com → tenant en producción
    """

    class Meta:
        verbose_name = "Dominio"
        verbose_name_plural = "Dominios"

    def __str__(self):
        return self.domain


class PlatformAdmin(models.Model):
    """
    Administrador del Panel de System Admin (ADR-013).

    Vive en el esquema `public` (apps.tenants es SHARED_APPS).
    Es independiente de users.User (TENANT_APPS) y de auth.User (swapped).
    El login se verifica con check_password() sobre el hash almacenado.

    JWT: RefreshToken.for_user() usa el pk como user_id. PlatformJWTAuthentication
    lo busca aqui por pk.
    """

    email = models.EmailField(unique=True, verbose_name="Email")
    password = models.CharField(max_length=128, verbose_name="Contrasena (hash)")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Propiedades que esperan las vistas y el authentication backend
    is_superuser = True
    is_staff = True
    is_authenticated = True
    is_anonymous = False

    class Meta:
        verbose_name = "Administrador de plataforma"
        verbose_name_plural = "Administradores de plataforma"

    def __str__(self):
        return f"PlatformAdmin({self.email})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class ComplexSettings(TimeStampedSoftDeleteModel):
    """
    Configuración pública y operativa del complejo deportivo.

    Vive en el esquema de CADA tenant (no en public). Contiene la información
    que el jugador puede ver (nombre del complejo, instrucciones de pago,
    contacto) y que el operador configura desde el panel de administración.

    El aislamiento por esquema garantiza una única instancia por tenant:
    no se usa unique_together porque cada esquema PostgreSQL es independiente.

    Uso típico:
        settings = ComplexSettings.objects.get_or_create(defaults={'complex_name': ''})[0]
    """

    complex_name = models.CharField(
        max_length=200,
        verbose_name="Nombre público del complejo",
        help_text="Nombre que verá el jugador en la grilla y en las notificaciones.",
    )
    payment_instructions = models.TextField(
        blank=True,
        default="",
        verbose_name="Instrucciones de pago",
        help_text=(
            "Texto libre con indicaciones para que el jugador pague la seña "
            "(ej: 'Transferí al CBU indicado y enviá el comprobante por WhatsApp')."
        ),
    )
    cbu_alias = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Alias CBU/CVU",
        help_text="Alias de la cuenta bancaria o billetera virtual del complejo.",
    )
    cbu_number = models.CharField(
        max_length=22,
        blank=True,
        default="",
        verbose_name="Número de CBU/CVU",
        help_text="CBU o CVU de 22 dígitos para transferencias bancarias.",
    )
    account_holder = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Titular de la cuenta",
        help_text="Nombre del titular de la cuenta bancaria o billetera.",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Teléfono de contacto",
        help_text="Número de teléfono del complejo (ej: +5491112345678).",
    )
    instagram = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Instagram",
        help_text="Usuario de Instagram sin el @. Ej: 'complejolospinos'.",
    )
    whatsapp = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="WhatsApp",
        help_text="Número de WhatsApp en formato internacional (ej: +5491112345678).",
    )

    class Meta:
        verbose_name = "Configuración del complejo"
        verbose_name_plural = "Configuraciones del complejo"

    def __str__(self):
        return f"Configuración: {self.complex_name or '(sin nombre)'}"


class UserEmailIndex(models.Model):
    """
    Índice global de emails de usuarios tenant (schema public).
    Permite que el login centralizado encuentre en qué tenant(s) existe un email.
    Permite emails duplicados entre tenants (unique por par email+schema).

    Sprint 14 — Login Centralizado.
    """

    email = models.EmailField()
    schema_name = models.CharField(max_length=63)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tenants"
        unique_together = [("email", "schema_name")]
        indexes = [models.Index(fields=["email"])]

    def __str__(self):
        return f"{self.email} → {self.schema_name}"


class OneTimeCode(models.Model):
    """
    Código de un solo uso para transferir el JWT entre subdominios.
    TTL: 60 segundos. Previene replay attacks con el flag `used`.

    Sprint 14 — Login Centralizado.
    """

    code = models.CharField(max_length=64, unique=True, db_index=True)
    schema_name = models.CharField(max_length=63)
    user_id = models.IntegerField()
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tenants"

    def __str__(self):
        return f"OTC({self.schema_name}, used={self.used})"
