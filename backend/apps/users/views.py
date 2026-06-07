"""
Views — app users

Sprint 0: vista de login por email (FIX R-08) + placeholders para Sprint 1+.

FIX R-08: EmailTokenObtainPairView reemplaza a TokenObtainPairView de SimpleJWT
para que el contrato del login sea {"email", "password"} → {access, refresh}.
Se registra en config/urls.py como POST /api/auth/login/.

Endpoints planificados (Sprint 1+):
  GET  /api/users/me/      — perfil del usuario autenticado
  POST /api/auth/register/ — registro de player (si se habilita auto-registro)
  GET  /api/users/         — listado de usuarios del tenant (solo tenant_admin)
"""

from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    """
    Vista de login por email+password → JWT (access + refresh).

    Endpoint: POST /api/auth/login/
    Cuerpo:   {"email": "...", "password": "..."}
    Respuesta: {"access": "...", "refresh": "..."}

    Reemplaza a TokenObtainPairView de SimpleJWT para usar el serializer
    custom que trabaja con email como identificador (FIX R-08, ADR-007).
    AllowAny: definido en urls.py (SimpleJWT lo hace por defecto también).
    """

    serializer_class = EmailTokenObtainPairSerializer
