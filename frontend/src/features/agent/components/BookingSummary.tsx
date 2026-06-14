/**
 * features/agent/components/BookingSummary.tsx
 * -----------------------------------------------
 * Recuadro informativo que indica qué reserva fue generada durante
 * una conversación del bot WhatsApp.
 *
 * Solo se renderiza si al menos un mensaje de la conversación tiene booking_id.
 * Muestra el último booking_id encontrado en la lista de mensajes.
 */

import { CalendarCheck } from 'lucide-react'

interface BookingSummaryProps {
  bookingId: number
}

export function BookingSummary({ bookingId }: BookingSummaryProps) {
  return (
    <div
      className="flex items-center gap-2 mx-4 my-3 px-4 py-3 rounded-xl border border-[#005c4b] bg-[#0d2e28]"
      role="note"
      aria-label={`Reserva ${bookingId} generada en esta conversación`}
    >
      <CalendarCheck size={18} className="shrink-0 text-[#25d366]" aria-hidden="true" />
      <p className="text-sm text-[#e9edef] font-medium">
        Reserva{' '}
        <span className="font-semibold text-[#25d366]">#{bookingId}</span>{' '}
        generada en esta conversación
      </p>
    </div>
  )
}
