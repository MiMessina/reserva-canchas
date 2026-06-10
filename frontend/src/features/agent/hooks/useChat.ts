/**
 * features/agent/hooks/useChat.ts
 * ---------------------------------
 * Custom hook que gestiona el estado del chat demo con el agente IA.
 *
 * Separa dos capas de estado:
 *  - messages      → burbujas visibles en la UI (solo user y assistant con texto)
 *  - apiMessages   → historial completo para el backend (incluye bloques de tool use)
 *
 * La separacion es necesaria porque Anthropic devuelve bloques internos
 * (tool_use, tool_result) que el backend necesita para mantener el contexto
 * pero que el usuario no debe ver en el chat.
 *
 * Logica principal:
 *  1. sendMessage: agrega el mensaje del usuario a ambas capas, llama a la API,
 *     agrega la respuesta visible a messages y actualiza apiMessages con el
 *     historial completo que devuelve el backend.
 *  2. clearChat: reinicia ambas capas y muestra el mensaje de bienvenida.
 */

import { useState, useCallback } from 'react'
import { sendChatMessage } from '../services/agentApi'
import type { ApiMessage, ChatMessage } from '../types'

// ─── Mensaje de bienvenida del asistente ──────────────────────────────────────

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    '¡Hola! Soy el asistente del complejo. ¿En qué te puedo ayudar? Podés consultarme disponibilidad, hacer o cancelar una reserva 🎾',
  timestamp: new Date(),
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Genera un ID unico para cada mensaje de la UI. */
function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

/**
 * Extrae el texto visible de la respuesta del asistente.
 * El contenido puede ser un string (mensaje simple) o un array de bloques
 * (cuando el modelo uso tools). Buscamos el primer bloque de tipo "text".
 */
function extractAssistantText(content: unknown): string {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    for (const block of content) {
      if (
        block &&
        typeof block === 'object' &&
        'type' in block &&
        block.type === 'text' &&
        'text' in block &&
        typeof block.text === 'string'
      ) {
        return block.text
      }
    }
  }
  return ''
}

// ─── Tipo del hook ────────────────────────────────────────────────────────────

export interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  error: string | null
  sendMessage: (text: string) => Promise<void>
  clearChat: () => void
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE])
  const [apiMessages, setApiMessages] = useState<ApiMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    setError(null)

    // Agregar el mensaje del usuario a la UI
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Construir el historial actualizado para la API
    const newApiMessages: ApiMessage[] = [
      ...apiMessages,
      { role: 'user', content: trimmed },
    ]

    setIsLoading(true)
    try {
      const response = await sendChatMessage({ messages: newApiMessages })

      // Actualizar el historial completo (incluye bloques internos de tool use)
      setApiMessages(response.messages)

      // Solo agregar el texto visible de la respuesta del asistente
      const lastAssistantMsg = [...response.messages]
        .reverse()
        .find((m) => m.role === 'assistant')
      const visibleText = response.reply || extractAssistantText(lastAssistantMsg?.content)

      if (visibleText) {
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: visibleText,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMessage])
      }
    } catch (err: unknown) {
      // Detectar el error 503 de API key no configurada
      let errorMessage = 'Ocurrio un error al contactar al asistente. Intenta de nuevo.'

      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as {
          response?: { status: number; data?: unknown }
        }
        const status = axiosError.response?.status
        const data = axiosError.response?.data

        if (status === 503 && data && typeof data === 'object' && 'error' in data) {
          const apiData = data as { error: string; message?: string }
          if (apiData.error === 'AGENT_NOT_CONFIGURED') {
            errorMessage =
              'El asistente aun no esta configurado. El administrador debe configurar la API key de Anthropic.'
          }
        } else if (status && status >= 500) {
          errorMessage = 'Error del servidor. Intenta de nuevo en unos momentos.'
        } else if (status === 401 || status === 403) {
          errorMessage = 'No tenes permiso para usar el asistente.'
        }
      }

      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [apiMessages, isLoading])

  const clearChat = useCallback(() => {
    setMessages([{ ...WELCOME_MESSAGE, timestamp: new Date() }])
    setApiMessages([])
    setError(null)
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
  }
}
