"""
views.py — ChatView: endpoint POST /api/agent/chat/

Recibe el historial de mensajes, ejecuta el agente y devuelve
la respuesta del asistente junto con el historial actualizado.

Requiere autenticación JWT (IsAuthenticated por defecto).
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent.serializers import ChatMessageSerializer
from apps.agent.services import run_agent

logger = logging.getLogger(__name__)


class ChatView(APIView):
    """
    POST /api/agent/chat/

    Body:
      { "messages": [{"role": "user", "content": "Hola"}, ...] }

    Response 200:
      { "reply": "¡Hola! ...", "messages": [...historial actualizado...] }

    Response 503:
      { "error": "AGENT_NOT_CONFIGURED", "message": "..." }

    Response 500:
      { "error": "AGENT_ERROR", "message": "..." }
    """

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        messages = serializer.validated_data["messages"]

        try:
            reply, updated_messages = run_agent(messages)
        except RuntimeError as exc:
            msg = str(exc)
            if "GEMINI_API_KEY" in msg or "gemini" in msg.lower():
                logger.error("Agente no configurado: %s", msg)
                return Response(
                    {
                        "error": "AGENT_NOT_CONFIGURED",
                        "message": msg,
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            logger.exception("Error en el agente: %s", msg)
            return Response(
                {
                    "error": "AGENT_ERROR",
                    "message": "El agente encontró un error. Intentá de nuevo.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Serializar el historial (solo strings desde la migración a Gemini)
        serializable_messages = _make_serializable(updated_messages)

        return Response(
            {
                "reply": reply,
                "messages": serializable_messages,
            }
        )


def _make_serializable(messages: list) -> list:
    """Pasa el historial tal como viene (solo strings desde la migración a Gemini)."""
    result = []
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        result.append({"role": msg["role"], "content": content})
    return result
