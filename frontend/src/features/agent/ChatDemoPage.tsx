/**
 * features/agent/ChatDemoPage.tsx
 * ---------------------------------
 * Pagina del chat demo con el agente IA. Ruta: /admin/agent
 *
 * Simula la apariencia de WhatsApp Web para mostrar como va a verse
 * el agente IA antes de conectar la integracion real con WhatsApp.
 *
 * Funcionalidad:
 *  - Header estilo WhatsApp con avatar del bot y estado "en linea".
 *  - Fondo de chat con patron sutil estilo WhatsApp.
 *  - Burbujas de usuario (derecha, verde) y asistente (izquierda, blanca).
 *  - Indicador "escribiendo..." animado mientras espera respuesta.
 *  - Banner de error amarillo si el backend devuelve 503 (API key no configurada).
 *  - Auto-scroll al ultimo mensaje.
 *  - Boton limpiar conversacion en el header.
 *
 * Estados:
 *  - loading: indicador "escribiendo..." con tres puntos animados
 *  - error: banner amarillo con el mensaje (sin bloquear el chat)
 */

import { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import { ChatHeader } from './components/ChatHeader'
import { ChatBubble } from './components/ChatBubble'
import { ChatInput } from './components/ChatInput'
import { useChat } from './hooks/useChat'

// ─── Indicador "escribiendo..." ───────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex justify-start" aria-live="polite" aria-label="El asistente esta escribiendo">
      <div
        className="px-4 py-3 rounded-t-2xl rounded-br-2xl rounded-bl-sm shadow-sm"
        style={{ backgroundColor: '#FFFFFF' }}
      >
        <div className="flex items-center gap-1" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function ChatDemoPage() {
  const { messages, isLoading, error, sendMessage, clearChat } = useChat()
  const bottomRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Auto-scroll al ultimo mensaje cada vez que cambia la lista o el estado de carga
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    // Contenedor que ocupa el area disponible dentro del AdminLayout
    <div className="flex flex-col h-[calc(100vh-4rem)] md:h-[calc(100vh-4rem)] overflow-hidden">

      {/* Header estilo WhatsApp */}
      <ChatHeader onClear={clearChat} />

      {/* Banner de error (API key no configurada u otro error) */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 px-4 py-2.5 text-sm bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-300 shrink-0"
        >
          <AlertTriangle size={16} className="shrink-0 mt-0.5" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* Area del chat — fondo estilo WhatsApp con patron sutil */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto px-3 py-4 space-y-2"
        style={{ backgroundColor: '#ECE5DD' }}
        role="list"
        aria-label="Mensajes del chat"
        aria-live="polite"
        aria-relevant="additions"
      >
        {/* Burbujas de mensajes */}
        {messages.map((message) => (
          <ChatBubble key={message.id} message={message} />
        ))}

        {/* Indicador "escribiendo..." */}
        {isLoading && <TypingIndicator />}

        {/* Ancla para el auto-scroll */}
        <div ref={bottomRef} aria-hidden="true" />
      </div>

      {/* Input fijo en la parte inferior */}
      <ChatInput onSend={(text) => void sendMessage(text)} disabled={isLoading} />
    </div>
  )
}
