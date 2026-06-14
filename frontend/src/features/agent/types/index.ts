/**
 * features/agent/types/index.ts
 * -------------------------------
 * Tipos del contrato de API del módulo visor de conversaciones del bot WhatsApp.
 * Consumidos por botApi.ts, useBotConversations.ts y los componentes del visor.
 *
 * Endpoint: GET /api/bot/conversations/
 */

/** Mensaje individual registrado por el bot. */
export interface BotMessage {
  id: number
  /** "inbound" = mensaje del jugador; "outbound" = respuesta del bot. */
  direction: 'inbound' | 'outbound'
  message: string
  /** ISO 8601 en UTC. Convertir a Buenos Aires en la capa de presentación. */
  created_at: string
  /** ID de la reserva generada durante esta conversación, o null si no aplica. */
  booking_id: number | null
}

/** Conversación agrupada por número de teléfono. */
export interface BotConversation {
  phone: string
  /** Nombre del jugador extraído por el bot, o cadena vacía si no se detectó. */
  player_name: string
  /** ISO 8601 en UTC. Indica cuándo llegó el último mensaje de esta conversación. */
  last_message_at: string
  messages: BotMessage[]
}
