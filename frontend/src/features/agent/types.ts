/**
 * features/agent/types.ts
 * ------------------------
 * Re-exporta los tipos del módulo de bot WhatsApp para compatibilidad
 * con cualquier import existente de "../types" dentro de esta feature.
 *
 * Los tipos del chat Gemini/Anthropic (ChatMessage, ApiMessage, etc.)
 * fueron deprecados en Sprint 5 (T5-04). Este archivo ya no los exporta.
 *
 * Para los tipos activos del visor del bot, usar:
 *   import type { BotConversation, BotMessage } from './types'
 */

export type { BotConversation, BotConversationsResponse, BotMessage } from './types/index'
