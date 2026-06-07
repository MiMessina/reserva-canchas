"""
Modelos del esquema `public` (compartido entre todos los tenants).

ADR-001: Multi-tenant por esquema PostgreSQL con django-tenants.
ADR-009: Alta de tenant por management command.

Reglas:
- Tenant y Domain viven SOLO en el esquema public.
- Toda entidad de negocio (User, Court, Booking, etc.) vive en el esquema
  del tenant correspondiente, NUNCA aquí.
- Soft-delete con is_active; prohibido DELETE físico.
"""

from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Tenant(TenantMixin):
    """
    Representa un complejo deportivo (cliente B2B del SaaS).

    Cada Tenant tiene su propio esquema PostgreSQL aislado.
    Los datos de negocio (canchas, reservas, caja, usuarios) viven
    dentro de ese esquema y son completamente inaccesibles desde otros.
    """

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
