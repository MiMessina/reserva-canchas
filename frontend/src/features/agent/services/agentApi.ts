/**
 * features/agent/services/agentApi.ts
 * -------------------------------------
 * Llamada al endpoint del agente IA.
 * Usa el cliente axios central (lib/axios.ts) con interceptor JWT.
 * No contiene logica de negocio: solo transporte HTTP.
 *
 * Endpoint:
 *   POST /api/agent/chat/   → tenant_admin / operator (JWT)
 *
 * El frontend envia el historial completo de mensajes (incluidos los bloques
 * internos de tool use) para que el backend/modelo tenga contexto completo.
 * El backend devuelve el historial actualizado y el texto de la respuesta.
 */

import apiClient from '@/lib/axios'
import type { AgentChatRequest, AgentChatResponse } from '../types'

export async function sendChatMessage(
  payload: AgentChatRequest,
): Promise<AgentChatResponse> {
  const { data } = await apiClient.post<AgentChatResponse>(
    '/agent/chat/',
    payload,
  )
  return data
}
