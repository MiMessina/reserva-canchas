/**
 * features/agent/services/botApi.ts
 * ------------------------------------
 * Llamadas al endpoint del visor de conversaciones del bot WhatsApp.
 * Usa el cliente Axios central (lib/axios.ts) con interceptor JWT.
 * No contiene lógica de negocio: solo transporte HTTP.
 *
 * Endpoints:
 *   GET    /api/bot/conversations/          → lista todas las conversaciones del tenant
 *   GET    /api/bot/conversations/?phone=X  → filtra por número de teléfono
 *   DELETE /api/bot/conversations/<phone>/  → soft-delete de una conversación (JWT)
 *
 * Requiere JWT (tenant_admin / operator).
 */

import apiClient from '@/lib/axios'
import type { BotConversationsResponse } from '../types'

/**
 * Obtiene las conversaciones del bot para el tenant activo.
 * @param phone - Filtro opcional por número de teléfono (formato "5491112345678@c.us").
 */
export async function fetchBotConversations(
  phone?: string,
): Promise<BotConversationsResponse> {
  const params: Record<string, string> = {}
  if (phone) params.phone = phone

  const { data } = await apiClient.get<BotConversationsResponse>(
    '/bot/conversations/',
    { params },
  )
  return data
}

/**
 * Elimina (soft-delete) todos los logs de la conversación con ese número.
 * @param phone - Número en formato whatsapp-web.js (ej: "5491112345678@c.us")
 */
export async function deleteConversation(phone: string): Promise<void> {
  await apiClient.delete(`/bot/conversations/${encodeURIComponent(phone)}/`)
}
