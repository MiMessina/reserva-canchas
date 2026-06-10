/**
 * features/agent/components/ChatBubble.tsx
 * ------------------------------------------
 * Burbuja de mensaje individual del chat demo.
 *
 * Mensajes del usuario: burbuja derecha, fondo verde (#DCF8C6).
 * Mensajes del asistente: burbuja izquierda, fondo blanco.
 * Muestra la hora del mensaje en formato HH:MM (America/Argentina/Buenos_Aires).
 */

import type { ChatMessage } from '../types'

interface ChatBubbleProps {
  message: ChatMessage
}

/** Formatea la hora del mensaje en HH:MM (horario de Buenos Aires). */
function formatTime(date: Date): string {
  return date.toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Argentina/Buenos_Aires',
  })
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={[
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start',
      ].join(' ')}
      role="listitem"
    >
      <div
        className={[
          'relative max-w-[78%] sm:max-w-[65%] px-3 py-2 shadow-sm',
          isUser
            ? 'rounded-t-2xl rounded-bl-2xl rounded-br-sm'
            : 'rounded-t-2xl rounded-br-2xl rounded-bl-sm',
        ].join(' ')}
        style={{
          backgroundColor: isUser ? '#DCF8C6' : '#FFFFFF',
        }}
      >
        {/* Texto del mensaje */}
        <p
          className="text-sm text-gray-800 whitespace-pre-wrap break-words leading-relaxed"
        >
          {message.content}
        </p>

        {/* Hora */}
        <p
          className="text-right mt-0.5 leading-none"
          style={{ fontSize: '11px', color: '#8696A0' }}
          aria-label={`Enviado a las ${formatTime(message.timestamp)}`}
        >
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  )
}
