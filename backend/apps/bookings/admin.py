"""
Admin — app bookings

Registra Booking y CashMovement en el panel de administración de Django.
El admin opera dentro del esquema del tenant activo (django-tenants).

CashMovement es inmutable: en el admin solo se permite lectura (readonly_fields).
"""

from django.contrib import admin

from apps.bookings.models import Booking, CashMovement


class CashMovementInline(admin.TabularInline):
    """Movimientos de caja en línea dentro del detalle de una reserva."""

    model = CashMovement
    extra = 0
    fields = ["operator", "amount", "notes", "created_at"]
    readonly_fields = ["operator", "amount", "notes", "created_at"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Administración de reservas."""

    list_display = [
        "id", "court", "status", "start_dt", "end_dt",
        "price", "user", "guest_name", "is_active", "created_at",
    ]
    list_filter = ["status", "court", "is_active"]
    search_fields = ["guest_name", "guest_phone", "user__email", "court__name"]
    ordering = ["-start_dt"]
    readonly_fields = ["start_dt", "end_dt", "price", "created_at", "updated_at"]
    inlines = [CashMovementInline]

    fieldsets = [
        (
            "Cancha y jugador",
            {
                "fields": ["court", "user", "guest_name", "guest_phone"],
            },
        ),
        (
            "Turno",
            {
                "fields": ["start_dt", "end_dt", "price"],
            },
        ),
        (
            "Estado",
            {
                "fields": ["status", "cancellation_reason", "is_active"],
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


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    """Administración de movimientos de caja (solo lectura)."""

    list_display = ["id", "booking", "operator", "amount", "notes", "created_at"]
    list_filter = ["operator"]
    search_fields = ["booking__id", "operator__email", "notes"]
    ordering = ["-created_at"]
    readonly_fields = ["booking", "operator", "amount", "notes", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
