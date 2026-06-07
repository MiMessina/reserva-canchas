/**
 * features/booking/pages/CashboxPage.tsx
 * ----------------------------------------
 * Caja diaria para operator/admin. Ruta: /admin/cashbox (requiere JWT).
 *
 * Funcionalidad:
 *  - Selector de fecha (default hoy).
 *  - Lista de movimientos del dia con monto (verde = positivo, rojo = negativo).
 *  - Total del dia: suma de todos los amounts.
 *  - Estados loading / empty / error.
 *
 * Un amount negativo indica una reversion o cancelacion confirmada.
 */

import { useState } from 'react'
import { Wallet, CalendarDays, TrendingUp, TrendingDown } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { useCashMovements } from '../hooks/useBookings'
import { formatTimeBA, toLocalDateStringBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function todayLocalDate(): string {
  return toLocalDateStringBA(new Date())
}

function formatARS(value: string): string {
  const num = parseFloat(value)
  if (isNaN(num)) return value
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
  }).format(num)
}

function sumAmounts(amounts: string[]): number {
  return amounts.reduce((acc, val) => acc + parseFloat(val || '0'), 0)
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function CashboxPage() {
  const [selectedDate, setSelectedDate] = useState<string>(todayLocalDate())

  const { data, isLoading, isError, error, refetch } =
    useCashMovements(selectedDate)

  const movements = data?.results ?? []
  const total = sumAmounts(movements.map((m) => m.amount))

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

        {/* Tarjeta de totales */}
        {!isLoading && !isError && movements.length > 0 && (
          <div
            aria-label="Total del dia"
            className={[
              'rounded-xl border px-5 py-4 flex items-center justify-between',
              total >= 0
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200',
            ].join(' ')}
          >
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Total del dia
              </p>
              <p
                className={[
                  'text-2xl font-bold mt-0.5',
                  total >= 0 ? 'text-green-700' : 'text-red-700',
                ].join(' ')}
              >
                {formatARS(String(total))}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {movements.length} movimiento{movements.length !== 1 ? 's' : ''}
              </p>
            </div>
            <span aria-hidden="true">
              {total >= 0 ? (
                <TrendingUp size={36} className="text-green-400" />
              ) : (
                <TrendingDown size={36} className="text-red-400" />
              )}
            </span>
          </div>
        )}

        {/* Estado de carga */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando movimientos..." />
          </div>
        )}

        {/* Estado de error */}
        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {/* Estado vacio */}
        {!isLoading && !isError && movements.length === 0 && (
          <EmptyState
            icon={<Wallet size={48} strokeWidth={1.5} />}
            title="Sin movimientos"
            description="No hay movimientos de caja para esta fecha."
          />
        )}

        {/* Lista de movimientos */}
        {!isLoading && !isError && movements.length > 0 && (
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
