"""
services.py — AgentService: orquesta el bucle de tool use con Claude API (ADR-012).

Flujo:
  1. Recibir historial de mensajes del frontend (stateless).
  2. Llamar a Claude con los TOOL_DEFINITIONS.
  3. Si Claude usa una tool → ejecutarla con execute_tool() → agregar resultado → repetir.
  4. Cuando Claude responde en texto → devolver reply + historial actualizado.

Sin modelos ni migraciones: el estado de la conversación vive en el frontend.
"""

import logging

from django.conf import settings

from apps.agent.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sos el asistente virtual de este complejo deportivo. Respondés por WhatsApp en nombre del complejo.

Tu trabajo es ayudar a los jugadores a:
- Ver la disponibilidad de canchas (pediles siempre una fecha específica si no la dan).
- Hacer una reserva (necesitás: cancha, fecha, hora, nombre y teléfono del jugador).
- Cancelar su reserva (pediles el teléfono con el que reservaron).
- Consultar el estado de su reserva (pediles el teléfono).

Reglas importantes:
- Siempre respondé en español rioplatense, de manera amigable y concisa (estilo WhatsApp).
- Antes de crear una reserva, confirmá los datos con el jugador: cancha, fecha, hora, nombre y teléfono.
- Si hay un error de negocio (turno ocupado, fuera de horario, etc.), explicalo en lenguaje simple y ofrecé alternativas.
- No inventés disponibilidad: siempre usá las tools para consultar datos reales.
- Las señas se pagan por transferencia bancaria; el cajero confirma la reserva al recibir el pago.
- No hablés de temas fuera del complejo deportivo."""

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
MAX_TOOL_ITERATIONS = 5


def run_agent(messages: list[dict]) -> tuple[str, list[dict]]:
    """
    Ejecuta el bucle de tool use del agente.

    Parámetros:
      messages — historial completo en formato Claude API:
                 [{"role": "user"|"assistant", "content": str | list}, ...]

    Retorna:
      (reply, updated_messages) donde:
        reply            — texto final del asistente para mostrar en el chat.
        updated_messages — historial actualizado (incluyendo tool calls/results y la respuesta).

    Lanza:
      RuntimeError si ANTHROPIC_API_KEY no está configurada.
      RuntimeError si Claude no converge después de MAX_TOOL_ITERATIONS.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY no está configurada. "
            "Agregá la variable de entorno en el archivo .env y reiniciá el servidor."
        )

    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "La librería 'anthropic' no está instalada. "
            "Agregá 'anthropic>=0.40,<1.0' a requirements.txt y reconstruí el contenedor."
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    current_messages = list(messages)
    iterations = 0

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=current_messages,
            tools=TOOL_DEFINITIONS,
        )

        if response.stop_reason == "end_turn":
            # Claude respondió con texto; extraer y retornar
            reply = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "",
            )
            current_messages.append({"role": "assistant", "content": response.content})
            return reply, current_messages

        if response.stop_reason == "tool_use":
            # Procesar todas las tool calls de esta respuesta
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info("Tool call: %s(%s)", block.name, block.input)
                    result_text = execute_tool(block.name, block.input)
                    logger.info("Tool result: %s", result_text[:200])
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        }
                    )

            # Agregar turno de asistente (con tool_use) y turno de usuario (con tool_results)
            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})
            continue

        # stop_reason inesperado
        logger.warning("stop_reason inesperado: %s", response.stop_reason)
        break

    raise RuntimeError(
        f"El agente no convergió después de {MAX_TOOL_ITERATIONS} iteraciones."
    )
