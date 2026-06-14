/**
 * features/agent/hooks/useBotConversations.ts
 * ---------------------------------------------
 * Hook para obtener y mantener actualizadas las conversaciones del bot WhatsApp.
 * Usa React Query con polling automático cada 5 segundos (refetchInterval).
 *
 * La invalidación manual no es necesaria porque el bot solo agrega mensajes
 * (no los modifica ni elimina); el polling mantiene la vista sincronizada.
 */

import { useQuery } from '@tanstack/react-query'
import { fetchBotConversations } from '../services/botApi'
import type { BotConversation } from '../types'

/** Intervalo de polling en milisegundos. */
const POLL_INTERVAL_MS = 5_000

export interface UseBotConversationsReturn {
  conversations: BotConversation[]
  isLoading: boolean
  isError: boolean
  /** Refresca manualmente la lista (útil para un botón "actualizar"). */
  refetch: () => void
}

export function useBotConversations(): UseBotConversationsReturn {
  const { data, isLoading, isError, refetch } = useQuery<BotConversation[]>({
    queryKey: ['bot-conversations'],
    queryFn: () => fetchBotConversations(),
    refetchInterval: POLL_INTERVAL_MS,
    // Mantener los datos anteriores visibles mientras se refresca (evita parpadeos).
    placeholderData: (previousData) => previousData,
  })

  return {
    conversations: data ?? [],
    isLoading,
    isError,
    refetch,
  }
}
