/**
 * features/agent/types.ts
 * ------------------------
 * Tipos del contrato de API del modulo de chat con el agente IA.
 *
 * El backend espera el historial completo de mensajes en cada request
 * (incluidos los bloques internos de tool use de Anthropic) para que
 * el modelo tenga contexto completo entre turnos.
 *
 * El frontend solo muestra los turnos visibles (user y assistant con texto);
 * los bloques internos se mantienen en apiMessages pero no se renderizan.
 */

// ─── Tipos de la API ─────────────────────────────────────────────────────────

/** Un bloque de contenido interno de Anthropic (text, tool_use, tool_result, etc.) */
export type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'tool_use'; id: string; name: string; input: unknown }
  | { type: 'tool_result'; tool_use_id: string; content: unknown }

/** Mensaje en el formato que espera y devuelve el backend */
export interface ApiMessage {
  role: string
  content: unknown  // string para user; ContentBlock[] para assistant con tool use
}

/** Payload del POST /api/agent/chat/ */
export interface AgentChatRequest {
  messages: ApiMessage[]
}

/** Respuesta exitosa del POST /api/agent/chat/ */
export interface AgentChatResponse {
  reply: string
  messages: ApiMessage[]
}

/** Respuesta de error 503 cuando ANTHROPIC_API_KEY no esta configurada */
export interface AgentErrorResponse {
  error: string
  message: string
}

// ─── Tipos de la UI ──────────────────────────────────────────────────────────

/** Mensaje visible en la burbuja del chat */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}
