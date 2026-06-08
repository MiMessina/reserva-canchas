/**
 * features/booking/pages/CashboxPage.tsx
 * ----------------------------------------
 * Caja diaria para operator/admin. Ruta: /admin/cashbox (requiere JWT).
 *
 * Funcionalidad:
 *  - Selector de fecha (default hoy).
 *  - Tarjeta de totales: ingresos, devoluciones y total neto — siempre visible,
 *    incluso con 0 movimientos. Los totales vienen del endpoint /summary/ del
 *    backend (correcto sin importar la paginación de la lista).
 *  - Lista de movimientos del dia con monto (verde = positivo, rojo = negativo).
 *  - Estados loading / empty / error independientes para tarjeta y lista.
 *
 * Un amount negativo indica una reversion o cancelacion de reserva confirmada.
 */

import { useState } from 'react'
import {
  Wallet,
  CalendarDays,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { useCashMovements, useCashMovementsSummary } from '../hooks/useBookings'
import { formatTimeBA, toLocalDateStringBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { CashDailySummary } from '../types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function todayLocalDate(): string {
  return toLocalDateStringBA(new Date())
}

function formatARS(value: string | number): string {
  const num = typeof value === 'number' ? value : parseFloat(value)
  if (isNaN(num)) return String(value)
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
  }).format(num)
}

// ─── Tarjeta de totales ───────────────────────────────────────────────────────

interface SummaryCardProps {
  isLoading: boolean
  isError: boolean
  summary?: CashDailySummary
}

function SummaryCard({ isLoading, isError, summary }: SummaryCardProps) {
  const total = summary ? parseFloat(summary.total) : 0
  const isNegative = total < 0

  // Placeholder cuando carga o hay error
  const placeholder = isLoading || isError || !summary

  return (
    <div
      aria-label="Resumen del dia"
      className="grid grid-cols-3 divide-x divide-gray-200 rounded-xl border border-gray-200 bg-white overflow-hidden"
    >
      {/* Ingresos */}
      <div className="px-4 py-3 text-center">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
          Ingresos
        </p>
        {placeholder ? (
          <p className="text-base font-bold text-gray-400 mt-1">—</p>
        ) : (
          <p className="text-base font-bold text-green-600 mt-1">
            {formatARS(summary.ingresos)}
          </p>
        )}
        <p className="text-xs text-gray-400 mt-0.5">
          {placeholder
            ? '—'
            : `${summary.ingresos_count} movimiento${summary.ingresos_count !== 1 ? 's' : ''}`}
        </p>
      </div>

      {/* Devoluciones */}
      <div className="px-4 py-3 text-center">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
          Devoluciones
        </p>
        {placeholder ? (
          <p className="text-base font-bold text-gray-400 mt-1">—</p>
        ) : (
          <p className="text-base font-bold text-red-600 mt-1">
            {parseFloat(summary.devoluciones) === 0
              ? formatARS('0')
              : formatARS(summary.devoluciones)}
          </p>
        )}
        <p className="text-xs text-gray-400 mt-0.5">
          {placeholder
            ? '—'
            : `${summary.devoluciones_count} reversion${summary.devoluciones_count !== 1 ? 'es' : ''}`}
        </p>
      </div>

      {/* Total neto */}
      <div className="px-4 py-3 text-center">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
          Total neto
        </p>
        {isLoading ? (
          <div className="flex justify-center mt-1">
            <Spinner size="sm" label="Cargando total..." />
          </div>
        ) : placeholder ? (
          <p className="text-base font-bold text-gray-400 mt-1">—</p>
        ) : (
          <p
            className={[
              'text-base font-bold mt-1',
              isNegative ? 'text-red-600' : 'text-gray-900',
            ].join(' ')}
          >
            {formatARS(summary.total)}
          </p>
        )}
        <p className="text-xs text-gray-400 mt-0.5 flex justify-center">
          {placeholder ? (
            '—'
          ) : isNegative ? (
            <TrendingDown size={14} className="text-red-400" aria-hidden="true" />
          ) : (
            <TrendingUp size={14} className="text-green-400" aria-hidden="true" />
          )}
        </p>
      </div>
    </div>
  )
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function CashboxPage() {
  const [selectedDate, setSelectedDate] = useState<string>(todayLocalDate())

  // Resumen: totales correctos sin importar la paginación de la lista.
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useCashMovementsSummary(selectedDate)

  // Lista de movimientos (paginada, solo la primera página en esta vista).
  const {
    data,
    isLoading: listLoading,
    isError: listError,
    error: listErrorObj,
    refetch,
  } = useCashMovements(selectedDate)

  const movements = data?.results ?? []

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          <Wallet size={20} className="text-brand-600" aria-hidden="true" />
          <h1 className="text-base font-semibold text-gray-900">Caja diaria</h1>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-5 space-y-5">
        {/* Selector de fecha */}
        <div className="space-y-1.5">
          <label
            htmlFor="cashbox-date"
            className="block text-sm font-medium text-gray-700"
          >
            Fecha
          </label>
          <div className="relative">
            <CalendarDays
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
              aria-hidden="true"
            />
            <input
              id="cashbox-date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>
        </div>

        {/* Tarjeta de totales — siempre visible */}
        <SummaryCard
          isLoading={summaryLoading}
          isError={summaryError}
          summary={summary}
        />

        {/* Lista de movimientos */}
        {listLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando movimientos..." />
          </div>
        )}

        {listError && !listLoading && (
          <ErrorState
            message={extractApiErrorMessage(listErrorObj)}
            onRetry={() => void refetch()}
          />
        )}

        {!listLoading && !listError && movements.length === 0 && (
          <EmptyState
            icon={<Wallet size={48} strokeWidth={1.5} />}
            title="Sin movimientos"
            description="No hay movimientos de caja para esta fecha."
          />
        )}

        {!listLoading && !listError && movements.length > 0 && (
          <section aria-label="Movimientos del dia">
            <ul className="space-y-2">
              {movements.map((movement) => {
                const amount = parseFloat(movement.amount)
                const isPositive = amount >= 0

                return (
                  <li
                    key={movement.id}
                    className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-start justify-between gap-3"
                  >
                    {/* Info del movimiento */}
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {movement.booking_court}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatTimeBA(movement.created_at)} &middot; por{' '}
                        <span className="text-gray-600">
                          {movement.operator_email}
                        </span>
                      </p>
                      {movement.notes && (
                        <p className="text-xs text-gray-400 italic truncate">
                          {movement.notes}
                        </p>
                      )}
                    </div>

                    {/* Monto */}
                    <div
                      className={[
                        'shrink-0 text-sm font-bold',
                        isPositive ? 'text-green-600' : 'text-red-600',
                      ].join(' ')}
                      aria-label={`Monto: ${formatARS(movement.amount)}`}
                    >
                      {isPositive ? '+' : ''}
                      {formatARS(movement.amount)}
                    </div>
                  </li>
                )
              })}
            </ul>
          </section>
        )}
      </main>
    </div>
  )
}
