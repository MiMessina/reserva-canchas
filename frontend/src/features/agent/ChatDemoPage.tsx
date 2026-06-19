/**
 * features/agent/ChatDemoPage.tsx  →  BotViewerPage
 * ---------------------------------------------------
 * Visor de conversaciones del bot WhatsApp. Ruta: /admin/agent
 *
 * Reemplaza el chat demo con Gemini/Anthropic. Ahora muestra, en tiempo real,
 * las conversaciones que el bot de WhatsApp (Node.js + Ollama) tiene con los
 * jugadores, consumiendo GET /api/bot/conversations/ con polling cada 5 s.
 *
 * Layout:
 *  - Desktop (md+): dos paneles lado a lado.
 *    Izquierdo (300 px): lista de conversaciones.
 *    Derecho (flex-1): mensajes de la conversación seleccionada.
 *  - Mobile: una sola columna. Si hay conversación seleccionada se muestra
 *    el panel de detalle a pantalla completa con botón "Volver".
 *
 * Estados contemplados:
 *  - loading inicial: skeleton en el panel izquierdo, placeholder en el derecho
 *  - empty: "Sin conversaciones aún. El bot aún no recibió mensajes."
 *  - error: banner rojo con mensaje genérico
 *  - conversación seleccionada: header + burbujas + BookingSummary (si aplica)
 *  - polling activo: los paneles se actualizan automáticamente sin parpadeo
 */

import { useState } from 'react'
import { AlertTriangle, ChevronLeft, FlaskConical, RefreshCw } from 'lucide-react'
import { ConversationList } from './components/ConversationList'
import { ConversationDetail } from './components/ConversationDetail'
import { useBotConversations } from './hooks/useBotConversations'

// ─── Página principal ─────────────────────────────────────────────────────────

export function ChatDemoPage() {
  const { conversations, botMode, isLoading, isError, refetch } = useBotConversations()
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null)

  // Conversación actualmente seleccionada (o null si no hay ninguna)
  const selectedConversation =
    conversations.find((c) => c.phone === selectedPhone) ?? null

  // En mobile: cuando se selecciona una conversación, se muestra solo el detalle.
  const showDetailOnMobile = selectedPhone !== null

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] md:h-[calc(100vh-4rem)] overflow-hidden bg-[#0b141a]">

      {/* Badge Modo Demo */}
      {botMode === 'mock' && (
        <div
          role="status"
          aria-label="Modo demostración activo"
          className="flex items-center gap-2 px-4 py-2 text-xs font-medium bg-amber-500/15 border-b border-amber-500/30 text-amber-300 shrink-0"
        >
          <FlaskConical size={13} className="shrink-0" aria-hidden="true" />
          <span>
            <strong className="font-semibold">Modo Demo</strong> — Mostrando conversaciones de prueba. Activá el modo Producción desde el panel de System Admin para ver mensajes reales.
          </span>
        </div>
      )}

      {/* Banner de error */}
      {isError && (
        <div
          role="alert"
          className="flex items-start gap-2 px-4 py-2.5 text-sm bg-red-900/30 border-b border-red-800 text-red-300 shrink-0"
        >
          <AlertTriangle size={16} className="shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            No se pudieron cargar las conversaciones. Verificá tu conexión e intentá de nuevo.
          </span>
          <button
            type="button"
            onClick={() => void refetch()}
            className="ml-auto flex items-center gap-1 text-xs font-medium underline underline-offset-2 hover:no-underline shrink-0"
            aria-label="Reintentar carga"
          >
            <RefreshCw size={12} aria-hidden="true" />
            Reintentar
          </button>
        </div>
      )}

      {/* Cuerpo: dos paneles */}
      <div className="flex flex-1 overflow-hidden">

        {/* Panel izquierdo */}
        <div
          className={[
            'flex-col h-full overflow-hidden',
            'w-full md:w-[300px] md:flex md:shrink-0',
            showDetailOnMobile ? 'hidden' : 'flex',
          ].join(' ')}
        >
          <ConversationList
            conversations={conversations}
            selectedPhone={selectedPhone}
            onSelect={setSelectedPhone}
            onDeselect={() => setSelectedPhone(null)}
            isLoading={isLoading}
          />
        </div>

        {/* Panel derecho */}
        <div
          className={[
            'flex-col h-full overflow-hidden flex-1',
            'md:flex',
            showDetailOnMobile ? 'flex' : 'hidden',
          ].join(' ')}
        >
          {/* Botón "Volver" solo en mobile */}
          {showDetailOnMobile && (
            <div className="md:hidden flex items-center px-3 py-2 border-b border-[#222e35] bg-[#202c33] shrink-0">
              <button
                type="button"
                onClick={() => setSelectedPhone(null)}
                className="flex items-center gap-1 text-sm font-medium text-[#aebac1] hover:text-[#e9edef] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#005c4b] rounded"
                aria-label="Volver a la lista de conversaciones"
              >
                <ChevronLeft size={18} aria-hidden="true" />
                Volver
              </button>
            </div>
          )}

          <div className="flex-1 overflow-hidden">
            <ConversationDetail conversation={selectedConversation} />
          </div>
        </div>
      </div>
    </div>
  )
}
