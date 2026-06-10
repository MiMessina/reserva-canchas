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
            if "ANTHROPIC_API_KEY" in msg or "anthropic" in msg.lower():
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

        # Convertir content de bloques Anthropic a formato serializable para JSON
        serializable_messages = _make_serializable(updated_messages)

        return Response(
            {
                "reply": reply,
                "messages": serializable_messages,
            }
        )


def _make_serializable(messages: list) -> list:
    """
    Convierte los objetos ContentBlock de Anthropic (no serializables por JSON)
    a dicts simples para poder incluirlos en la Response.
    """
    result = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            result.append({"role": msg["role"], "content": content})
        elif isinstance(content, list):
            serialized_content = []
            for block in content:
                if hasattr(block, "model_dump"):
                    serialized_content.append(block.model_dump())
                elif isinstance(block, dict):
                    serialized_content.append(block)
                else:
                    serialized_content.append({"type": "unknown", "text": str(block)})
            result.append({"role": msg["role"], "content": serialized_content})
        else:
            result.append({"role": msg["role"], "content": str(content)})
    return result
