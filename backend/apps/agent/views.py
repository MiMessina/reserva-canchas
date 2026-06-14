"""
views.py — agente IA y bot WhatsApp

Vistas:
  ChatView                  POST   /api/agent/chat/                (deprecado — devuelve 410 Gone)
  BotLogView                POST   /api/bot/log/                   (log de mensajes bot, AllowAny)
  BotConversationsView      GET    /api/bot/conversations/         (visor agrupado, JWT requerido)
  BotConversationDeleteView DELETE /api/bot/conversations/<phone>/ (soft-delete, JWT requerido)
"""

import logging
from itertools import groupby

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent.models import BotConversationLog
from apps.agent.serializers import (
    BotConversationSerializer,
    BotLogCreateSerializer,
)

logger = logging.getLogger(__name__)


class ChatView(APIView):
    """Chat demo — deprecado. Usar el visor del bot WhatsApp."""

    def post(self, request):
        return Response(
            {
                "error": "DEPRECATED",
                "message": "El chat con IA fue reemplazado por el visor del bot WhatsApp.",
            },
            status=status.HTTP_410_GONE,
        )


# ---------------------------------------------------------------------------
# Vistas del bot WhatsApp (T5-02)
# ---------------------------------------------------------------------------


class BotLogView(APIView):
    """
    POST /api/bot/log/

    Registra un mensaje individual del bot o del jugador en el esquema del
    tenant activo. No requiere JWT porque el bot Node.js no tiene token.

    Body:
      {
        "phone":       "5491112345678@c.us",  (requerido)
        "direction":   "inbound" | "outbound", (requerido)
        "message":     "Hola, quiero reservar", (requerido)
        "player_name": "Juan",                 (opcional)
        "booking_id":  42                      (opcional)
      }

    Response 201:
      { "id": 1, "phone": "...", "direction": "inbound", "message": "...",
        "player_name": "", "booking_id": null, "created_at": "..." }

    Response 400:
      Errores de validación estándar DRF.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BotLogCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        log = serializer.save()
        out = BotLogCreateSerializer(log)
        return Response(out.data, status=status.HTTP_201_CREATED)


class BotConversationsView(APIView):
    """
    GET /api/bot/conversations/

    Devuelve conversaciones agrupadas por phone, ordenadas por el mensaje
    más reciente DESC. Requiere JWT (solo admin/operador).

    Query params:
      ?phone=5491112345678@c.us  — filtrar por número exacto (opcional)

    Response 200:
      [
        {
          "phone": "5491112345678@c.us",
          "player_name": "Juan",
          "last_message_at": "2026-06-13T20:00:00Z",
          "messages": [
            { "id": 1, "direction": "inbound", "message": "Hola",
              "created_at": "...", "booking_id": null },
            ...
          ]
        },
        ...
      ]
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = BotConversationLog.objects.filter(is_active=True).order_by("phone", "created_at")

        phone_filter = request.query_params.get("phone")
        if phone_filter:
            qs = qs.filter(phone=phone_filter)

        # Agrupar en Python por phone (MVP: volumen bajo)
        conversations = []
        for phone, msgs_iter in groupby(qs, key=lambda m: m.phone):
            msgs = list(msgs_iter)  # ya ordenados por created_at ASC dentro del grupo

            # player_name: el más reciente que no esté vacío
            player_name = ""
            for m in reversed(msgs):
                if m.player_name:
                    player_name = m.player_name
                    break

            last_message_at = msgs[-1].created_at

            conversations.append(
                {
                    "phone": phone,
                    "player_name": player_name,
                    "last_message_at": last_message_at,
                    "messages": msgs,
                }
            )

        # Ordenar conversaciones por last_message_at DESC
        conversations.sort(key=lambda c: c["last_message_at"], reverse=True)

        serializer = BotConversationSerializer(conversations, many=True)
        return Response(serializer.data)


class BotConversationDeleteView(APIView):
    """
    DELETE /api/bot/conversations/<phone>/

    Soft-delete de todos los logs activos del número indicado.
    El phone viene URL-encoded en la ruta (ej: 5491112345678%40c.us).
    Requiere JWT (tenant_admin u operator).

    Response 204: borrado exitoso
    Response 404: no existe ningún log activo para ese phone
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, phone: str):
        updated = BotConversationLog.objects.filter(
            phone=phone, is_active=True
        ).update(is_active=False)

        if not updated:
            return Response(
                {"error": "NOT_FOUND", "message": "No hay conversaciones activas para ese número."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
