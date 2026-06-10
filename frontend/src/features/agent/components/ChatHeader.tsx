/**
 * features/agent/components/ChatHeader.tsx
 * ------------------------------------------
 * Header fijo del chat demo, estilo WhatsApp Web.
 *
 * Muestra el avatar del bot, nombre del asistente, estado "en linea"
 * y la aclaracion "Vista previa". El boton de papelera limpia la conversacion.
 */

import { Bot, Trash2 } from 'lucide-react'

interface ChatHeaderProps {
  onClear: () => void
}

export function ChatHeader({ onClear }: ChatHeaderProps) {
  return (
    <header
      className="flex items-center gap-3 px-4 py-3 shrink-0"
      style={{ backgroundColor: '#075E54' }}
      role="banner"
    >
      {/* Avatar del bot */}
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
        style={{ backgroundColor: '#128C7E' }}
        aria-hidden="true"
      >
        <Bot size={22} className="text-white" />
      </div>

      {/* Nombre y estado */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white leading-tight truncate">
          Asistente CanchaYA
        </p>
        <p className="text-xs leading-tight" style={{ color: '#A8D5CF' }}>
          En linea &middot; Vista previa
        </p>
      </div>

      {/* Boton limpiar conversacion */}
      <button
        type="button"
        onClick={onClear}
        aria-label="Limpiar conversacion"
        title="Limpiar conversacion"
        className="shrink-0 p-2 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/50"
      >
        <Trash2 size={18} aria-hidden="true" />
      </button>
    </header>
  )
}
