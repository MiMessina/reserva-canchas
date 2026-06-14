/**
 * features/agent/components/ConversationList.tsx
 * -------------------------------------------------
 * Panel izquierdo del visor de conversaciones del bot WhatsApp.
 *
 * Paleta visual: dark mode real de WhatsApp Web.
 * Incluye botón de papelera (visible en hover) para soft-delete de conversaciones.
 */

import { useState } from 'react'
import { MessageCircle, Trash2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { BotConversation } from '../types'
import { formatTimeBA } from '@/lib/datetime'
import { formatPhone } from '@/lib/formatPhone'
import { deleteConversation } from '../services/botApi'

interface ConversationListProps {
  conversations: BotConversation[]
  selectedPhone: string | null
  onSelect: (phone: string) => void
  onDeselect: () => void
  isLoading: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(utcIso: string): string {
  const diffMs = Date.now() - new Date(utcIso).getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60) return 'ahora'
  if (diffSec < 3600) return `hace ${Math.floor(diffSec / 60)} min`
  if (diffSec < 86_400) return `hace ${Math.floor(diffSec / 3600)} hs`
  return formatTimeBA(utcIso)
}

function previewText(text: string, maxLen = 45): string {
  return text.length > maxLen ? `${text.slice(0, maxLen)}…` : text
}

function displayName(conv: BotConversation): string {
  return conv.player_name || formatPhone(conv.phone)
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ConversationSkeleton() {
  return (
    <div className="animate-pulse" aria-hidden="true">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-4 py-3 border-b border-[#222e35]"
        >
          <div className="w-10 h-10 rounded-full bg-[#2a3942] shrink-0" />
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="h-3.5 bg-[#2a3942] rounded w-2/3" />
            <div className="h-3 bg-[#202c33] rounded w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function ConversationList({
  conversations,
  selectedPhone,
  onSelect,
  onDeselect,
  isLoading,
}: ConversationListProps) {
  const queryClient = useQueryClient()
  const [hoveredPhone, setHoveredPhone] = useState<string | null>(null)

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_data, phone) => {
      // Si se borró la conversación activa, deseleccionar
      if (phone === selectedPhone) onDeselect()
      void queryClient.invalidateQueries({ queryKey: ['bot-conversations'] })
    },
  })

  const handleDelete = (e: React.MouseEvent, phone: string) => {
    e.stopPropagation()
    deleteMutation.mutate(phone)
  }

  return (
    <aside
      className="flex flex-col h-full border-r border-[#222e35] bg-[#111b21]"
      aria-label="Lista de conversaciones"
    >
      {/* Encabezado */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#222e35] shrink-0">
        <MessageCircle size={18} className="text-[#aebac1] shrink-0" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-[#e9edef]">Conversaciones</h2>
        {!isLoading && conversations.length > 0 && (
          <span className="ml-auto text-xs font-medium text-[#8696a0] bg-[#202c33] px-2 py-0.5 rounded-full">
            {conversations.length}
          </span>
        )}
      </div>

      {/* Contenido */}
      <div className="flex-1 overflow-y-auto" role="list">
        {isLoading ? (
          <ConversationSkeleton />
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-6 py-12 text-center">
            <MessageCircle size={40} className="text-[#8696a0] mb-3" aria-hidden="true" />
            <p className="text-sm font-medium text-[#e9edef]">Sin conversaciones aún</p>
            <p className="text-xs text-[#8696a0] mt-1">
              El bot aún no recibió mensajes de WhatsApp.
            </p>
          </div>
        ) : (
          conversations.map((conv) => {
            const isSelected = conv.phone === selectedPhone
            const isHovered = conv.phone === hoveredPhone
            const lastMsg = conv.messages.at(-1)
            const name = displayName(conv)

            return (
              <button
                key={conv.phone}
                type="button"
                role="listitem"
                onClick={() => onSelect(conv.phone)}
                onMouseEnter={() => setHoveredPhone(conv.phone)}
                onMouseLeave={() => setHoveredPhone(null)}
                aria-current={isSelected ? 'true' : undefined}
                aria-label={`Conversación con ${name}`}
                className={[
                  'w-full flex items-center gap-3 px-4 py-3 text-left',
                  'border-b border-[#222e35]',
                  'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#005c4b]',
                  isSelected
                    ? 'bg-[#2a3942]'
                    : 'hover:bg-[#202c33]',
                ].join(' ')}
              >
                {/* Avatar con inicial */}
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 text-sm font-semibold bg-[#6b7c85] text-white"
                  aria-hidden="true"
                >
                  {name.charAt(0).toUpperCase()}
                </div>

                {/* Nombre, preview y timestamp */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-1">
                    <span className="text-sm font-semibold truncate text-[#e9edef]">
                      {name}
                    </span>
                    <span className="text-xs text-[#8696a0] shrink-0">
                      {relativeTime(conv.last_message_at)}
                    </span>
                  </div>
                  {lastMsg && (
                    <p className="text-xs text-[#8696a0] truncate mt-0.5">
                      {lastMsg.direction === 'outbound' && (
                        <span className="text-[#aebac1] font-medium mr-0.5">Bot:</span>
                      )}
                      {previewText(lastMsg.message)}
                    </p>
                  )}
                </div>

                {/* Botón papelera (visible en hover) */}
                {isHovered && (
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, conv.phone)}
                    disabled={deleteMutation.isPending}
                    aria-label={`Borrar conversación con ${name}`}
                    className="ml-1 p-1 rounded shrink-0 text-[#8696a0] hover:text-red-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                )}
              </button>
            )
          })
        )}
      </div>
    </aside>
  )
}
