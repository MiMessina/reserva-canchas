/**
 * features/agent/components/ChatInput.tsx
 * -----------------------------------------
 * Campo de entrada del chat demo.
 *
 * - Enter para enviar, Shift+Enter para nueva linea.
 * - Boton de envio con icono Send de Lucide.
 * - Deshabilitado mientras disabled=true (esperando respuesta).
 * - Fondo blanco, pegado al fondo del chat.
 */

import { useState, useRef, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleSend() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    // Resetear la altura del textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sin Shift: enviar
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleInput() {
    // Auto-resize del textarea (maximo 5 lineas aprox.)
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  return (
    <div
      className="flex items-end gap-2 px-3 py-2 border-t border-gray-200 bg-white shrink-0"
      role="form"
      aria-label="Campo de mensaje"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder="Escribi un mensaje..."
        rows={1}
        aria-label="Escribi tu mensaje"
        className={[
          'flex-1 resize-none rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5',
          'text-sm text-gray-800 placeholder-gray-400 leading-relaxed',
          'focus:outline-none focus:ring-2 focus:border-transparent',
          'disabled:opacity-60 disabled:cursor-not-allowed',
          'transition-colors max-h-[120px] overflow-y-auto',
        ].join(' ')}
        style={{
          // El ring de foco usa el verde de WhatsApp
          // (no se puede hacer con Tailwind arbitrario en ring dinamico)
        }}
      />
      <button
        type="button"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Enviar mensaje"
        className={[
          'flex items-center justify-center w-10 h-10 rounded-full shrink-0 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-offset-1',
          disabled || !value.trim()
            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
            : 'text-white hover:opacity-90 active:opacity-80',
        ].join(' ')}
        style={
          !(disabled || !value.trim())
            ? { backgroundColor: '#075E54', outline: 'none' }
            : undefined
        }
      >
        <Send size={18} aria-hidden="true" />
      </button>
    </div>
  )
}
