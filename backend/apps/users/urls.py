"""
URLs — app users

Rutas generadas:
  GET    /api/users/me/     — perfil del usuario autenticado (IsAuthenticated)
  GET    /api/users/        — lista de operadores activos (IsTenantAdmin)
  POST   /api/users/        — crear operador (IsTenantAdmin)
  GET    /api/users/{id}/   — detalle de operador (IsTenantAdmin)
  PATCH  /api/users/{id}/   — editar operador (IsTenantAdmin)
  DELETE /api/users/{id}/   — soft-delete (IsTenantAdmin)

Incluido en config/urls.py con:
    path("api/", include("apps.users.urls"))

Nota: el endpoint me/ se registra como @action en el ViewSet; el router
lo genera automáticamente como /api/users/me/.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.users.views import UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
]
