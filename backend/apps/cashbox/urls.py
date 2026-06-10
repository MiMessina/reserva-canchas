"""
URLs — app cashbox

Endpoints de sesiones de caja:
  POST /api/cash-sessions/open/    — abrir sesión (operator/tenant_admin)
  POST /api/cash-sessions/close/   — cerrar sesión (operator/tenant_admin)
  GET  /api/cash-sessions/today/   — sesión del día o 404 (operator/tenant_admin)
  GET  /api/cash-sessions/         — historial paginado (operator/tenant_admin)

Nota: las rutas custom (open, close, today) se registran como @action en el
ViewSet y se generan automáticamente por el router. Las acciones declaradas
con url_path explícito en el ViewSet tienen precedencia.
"""

from rest_framework.routers import DefaultRouter

from apps.cashbox.views import CashSessionViewSet

router = DefaultRouter()
router.register(r"cash-sessions", CashSessionViewSet, basename="cash-session")

urlpatterns = router.urls
