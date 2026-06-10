"""
URLs — app bookings

Registra los ViewSets de Booking y CashMovement con DefaultRouter,
y las views de disponibilidad, dashboard, grilla multi-cancha y reporte semanal
como rutas explícitas.

Rutas generadas:
  GET    /api/bookings/                         — listado (admin/operator)
  POST   /api/bookings/                         — crear reserva (AllowAny)
  GET    /api/bookings/{id}/                    — detalle
  POST   /api/bookings/{id}/confirm/            — confirmar (operator/admin)
  POST   /api/bookings/{id}/cancel/             — cancelar
  POST   /api/bookings/{id}/complete/           — completar (operator/admin)
  GET    /api/bookings/guest-lookup/?phone=XXXX — reservas del invitado por teléfono (público)
  POST   /api/bookings/{id}/cancel-guest/       — cancelar reserva propia por teléfono (público)
  GET    /api/cash-movements/                   — caja (operator/admin)
  GET    /api/cash-movements/export/            — exportar CSV (operator/admin)
  GET    /api/dashboard/                        — resumen del día (operator/admin)
  GET    /api/bookings/daily-grid/              — grilla multi-cancha del día (operator/admin)
  GET    /api/bookings/weekly-report/           — reporte semanal de ocupación y caja (operator/admin)
  GET    /api/courts/{court_id}/availability/?date=YYYY-MM-DD  — grilla (AllowAny)

Incluido en config/urls.py con:
    path("api/", include("apps.bookings.urls"))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.bookings.views import (
    AvailabilityView,
    BookingViewSet,
    CancelGuestView,
    CashMovementViewSet,
    DailyGridView,
    DashboardView,
    GuestLookupView,
    WeeklyReportView,
)

router = DefaultRouter()
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"cash-movements", CashMovementViewSet, basename="cash-movement")

urlpatterns = [
    # Las rutas explícitas deben preceder a include(router.urls) para evitar que
    # el patrón genérico {pk}/ del router capture rutas como bookings/daily-grid/.
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("bookings/daily-grid/", DailyGridView.as_view(), name="booking-daily-grid"),
    path("bookings/weekly-report/", WeeklyReportView.as_view(), name="bookings-weekly-report"),
    # Rutas públicas de invitados (AllowAny) — deben ir ANTES del router para
    # que guest-lookup no sea capturado como {pk}/ y cancel-guest tampoco.
    path("bookings/guest-lookup/", GuestLookupView.as_view(), name="bookings-guest-lookup"),
    path("bookings/<int:pk>/cancel-guest/", CancelGuestView.as_view(), name="bookings-cancel-guest"),
    path(
        "courts/<int:court_id>/availability/",
        AvailabilityView.as_view(),
        name="court-availability",
    ),
    path("", include(router.urls)),
]
