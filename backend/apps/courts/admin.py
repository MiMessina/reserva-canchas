"""
Admin — app courts

Registra Court y ScheduleBlock en el panel de administración de Django.
El admin opera dentro del esquema del tenant activo (django-tenants).

Nota: el panel de Django admin está habilitado por tenant (TENANT_APPS incluye
django.contrib.admin). El system_admin accede al admin del esquema public para
gestionar Tenants/Domains; el tenant_admin puede acceder al admin de su esquema.
"""

from django.contrib import admin

from apps.courts.models import Court, ScheduleBlock


class ScheduleBlockInline(admin.TabularInline):
    """Bloques horarios en línea dentro del detalle de una cancha."""

    model = ScheduleBlock
    extra = 0
    fields = ["weekday", "open_time", "close_time", "is_active"]
    ordering = ["weekday", "open_time"]


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    """Administración de canchas."""

    list_display = ["name", "court_type", "surface", "base_price", "slot_duration_minutes", "is_active", "created_at"]
    list_filter = ["court_type", "is_active"]
    search_fields = ["name", "surface"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ScheduleBlockInline]

    fieldsets = [
        (
            "Datos de la cancha",
            {
                "fields": ["name", "court_type", "surface"],
            },
        ),
        (
            "Precio y duración",
            {
                "fields": ["base_price", "slot_duration_minutes"],
            },
        ),
        (
            "Estado",
            {
                "fields": ["is_active"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(ScheduleBlock)
class ScheduleBlockAdmin(admin.ModelAdmin):
    """Administración de bloques horarios."""

    list_display = ["court", "weekday", "open_time", "close_time", "is_active", "created_at"]
    list_filter = ["court", "weekday", "is_active"]
    search_fields = ["court__name"]
    ordering = ["court", "weekday", "open_time"]
    readonly_fields = ["created_at", "updated_at"]
