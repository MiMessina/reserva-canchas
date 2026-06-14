/**
 * features/agent/components/ConversationDetail.tsx
 * ---------------------------------------------------
 * Panel derecho del visor de conversaciones del bot WhatsApp.
 * Paleta visual: dark mode real de WhatsApp Web.
 */

import { useEffect, useRef } from 'react'
import { MessageCircle } from 'lucide-react'
import { BookingSummary } from './BookingSummary'
import { formatTimeBA } from '@/lib/datetime'
import { formatPhone } from '@/lib/formatPhone'
import type { BotConversation, BotMessage } from '../types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function displayName(conv: BotConversation): string {
  return conv.player_name || formatPhone(conv.phone)
}

function extractLastBookingId(messages: BotMessage[]): number | null {
  return (
    [...messages].reverse().find((m) => m.booking_id !== null)?.booking_id ??
    null
  )
}

// ─── Burbuja individual ───────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: BotMessage }) {
  const isOutbound = msg.direction === 'outbound'

  return (
    <div
      className={['flex w-full', isOutbound ? 'justify-end' : 'justify-start'].join(' ')}
      role="listitem"
    >
      <div
        className={[
          'relative max-w-[78%] sm:max-w-[65%] px-3 py-2 shadow-sm',
          isOutbound
            ? 'rounded-t-2xl rounded-bl-2xl rounded-br-sm'
            : 'rounded-t-2xl rounded-br-2xl rounded-bl-sm',
        ].join(' ')}
        style={{ backgroundColor: isOutbound ? '#005c4b' : '#202c33' }}
      >
        <span className="sr-only">{isOutbound ? 'Bot:' : 'Jugador:'}</span>

        <p className="text-sm text-[#e9edef] whitespace-pre-wrap break-words leading-relaxed">
          {msg.message}
        </p>

        <p
          className="text-right mt-0.5 leading-none"
          style={{ fontSize: '11px', color: '#8696a0' }}
          aria-label={`Enviado a las ${formatTimeBA(msg.created_at)}`}
        >
          {formatTimeBA(msg.created_at)}
        </p>
      </div>
    </div>
  )
}

// ─── Placeholder ──────────────────────────────────────────────────────────────

function EmptyDetail() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center select-none">
      <MessageCircle size={48} className="text-[#8696a0] mb-4" aria-hidden="true" />
      <p className="text-sm font-medium text-[#e9edef]">Seleccioná una conversación</p>
      <p className="text-xs text-[#8696a0] mt-1">Los mensajes aparecerán acá.</p>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

interface ConversationDetailProps {
  conversation: BotConversation | null
}

export function ConversationDetail({ conversation }: ConversationDetailProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages.length, conversation?.phone])

  if (!conversation) {
    return (
      <section className="flex flex-col h-full bg-[#0b141a]">
        <EmptyDetail />
      </section>
    )
  }

  const name = displayName(conversation)
  const lastBookingId = extractLastBookingId(conversation.messages)

  return (
    <section className="flex flex-col h-full" aria-label={`Conversación con ${name}`}>
      {/* Header */}
      <header
        className="flex items-center gap-3 px-4 py-3 border-b border-[#222e35] bg-[#202c33] shrink-0"
        role="banner"
      >
        <div
          className="w-9 h-9 rounded-full bg-[#6b7c85] flex items-center justify-center text-sm font-semibold text-white shrink-0"
          aria-hidden="true"
        >
          {name.charAt(0).toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[#e9edef] leading-tight truncate">
            {name}
          </p>
          <p className="text-xs text-[#8696a0] leading-tight truncate">
            {formatPhone(conversation.phone)}
          </p>
        </div>
      </header>

      {/* Recuadro de reserva */}
      {lastBookingId !== null && (
        <BookingSummary bookingId={lastBookingId} />
      )}

      {/* Área de mensajes */}
      <div
        className="flex-1 overflow-y-auto px-3 py-4 space-y-2 bg-[#0b141a]"
        role="list"
        aria-label="Mensajes de la conversación"
        aria-live="polite"
        aria-relevant="additions"
      >
        {conversation.messages.length === 0 ? (
          <p className="text-center text-xs text-[#8696a0] mt-8">
            No hay mensajes en esta conversación.
          </p>
        ) : (
          conversation.messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))
        )}
        <div ref={bottomRef} aria-hidden="true" />
      </div>
    </section>
  )
}
