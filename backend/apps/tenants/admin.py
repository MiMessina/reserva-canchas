"""
Admin de la app tenants (esquema public).

Registra Tenant y Domain en el Django Admin para que el system_admin
pueda gestionar complejos desde /admin/.

El alta principal de tenants se hace con el management command create_tenant
(ADR-009), pero el admin sirve para consultas y ajustes operativos.
"""

from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from .models import Domain, Tenant


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("name", "schema_name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "schema_name")
    readonly_fields = ("schema_name", "created_at", "updated_at")
    inlines = [DomainInline]


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain",)
