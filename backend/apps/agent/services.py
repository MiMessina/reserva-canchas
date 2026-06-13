"""
services.py — AgentService: orquesta el bucle de function calling con Gemini API (ADR-012).

Usa el SDK google-genai (v1 estable). Flujo:
  1. Recibir historial de mensajes del frontend (stateless).
  2. Llamar a Gemini con las TOOL_DEFINITIONS.
  3. Si Gemini llama una function → ejecutarla → devolver resultado → repetir.
  4. Cuando Gemini responde en texto → devolver reply + historial actualizado.

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

MODEL = "gemini-2.0-flash"
MAX_TOOL_ITERATIONS = 5


def run_agent(messages: list[dict]) -> tuple[str, list[dict]]:
    """
    Ejecuta el bucle de function calling del agente con Gemini (google-genai SDK).

    Parámetros:
      messages — historial: [{"role": "user"|"assistant", "content": str}, ...]
                 El último elemento debe ser el mensaje nuevo del usuario.

    Retorna:
      (reply, updated_messages) donde updated_messages incluye la respuesta appended.

    Lanza:
      RuntimeError si GEMINI_API_KEY no está configurada.
      RuntimeError si el agente no converge después de MAX_TOOL_ITERATIONS.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY no está configurada. "
            "Agregá la variable de entorno en el archivo .env y reiniciá el servidor."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "La librería 'google-genai' no está instalada. "
            "Agregá 'google-genai>=1.0.0' a requirements.txt y reconstruí el contenedor."
        )

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Construir lista de Contents para Gemini desde el historial
    # Gemini usa "model" (no "assistant") y types.Content/Part
    contents = []
    for msg in messages:
        content_text = msg.get("content", "")
        if not isinstance(content_text, str):
            continue
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=content_text)])
        )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOL_DEFINITIONS],
    )

    iterations = 0
    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]

        # Detectar function calls
        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if part.function_call and part.function_call.name
        ]

        if function_calls:
            # Agregar el turno del modelo con las function calls al historial
            contents.append(candidate.content)

            # Ejecutar cada function call y construir la respuesta
            function_response_parts = []
            for fc in function_calls:
                logger.info("Function call: %s(%s)", fc.name, dict(fc.args))
                result_text = execute_tool(fc.name, dict(fc.args))
                logger.info("Function result: %s", result_text[:200])
                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result_text},
                        )
                    )
                )

            # Agregar las respuestas como turno de usuario
            contents.append(
                types.Content(role="user", parts=function_response_parts)
            )
            continue

        # Respuesta de texto final
        reply = candidate.content.parts[0].text if candidate.content.parts else ""

        # Historial actualizado: solo strings (el último assistant se agrega)
        updated_messages = list(messages) + [{"role": "assistant", "content": reply}]
        return reply, updated_messages

    raise RuntimeError(
        f"El agente no convergió después de {MAX_TOOL_ITERATIONS} iteraciones."
    )
