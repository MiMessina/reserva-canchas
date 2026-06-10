/**
 * features/booking/pages/CashboxPage.tsx
 * ----------------------------------------
 * Caja diaria para operator/admin. Ruta: /admin/cashbox (requiere JWT).
 *
 * Funcionalidad:
 *  - Bloque de sesión de caja: apertura/cierre de sesión del día (CashSession).
 *    · Sin sesión → botón "Abrir caja" con modal de monto inicial.
 *    · Sesión OPEN → tarjeta verde + botón "Cerrar caja" con modal de monto contado.
 *    · Sesión CLOSED → tarjeta gris con resumen (diferencia verde/roja).
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
  Download,
  Lock,
  LockOpen,
  AlertCircle,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { Modal } from '@/components/Modal'
import { Button } from '@/components/Button'
import { useCashMovements, useCashMovementsSummary } from '../hooks/useBookings'
import { formatTimeBA, formatDateTimeBA, toLocalDateStringBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'
import apiClient from '@/lib/axios'
import {
  getCashSessionToday,
  openCashSession,
  closeCashSession,
} from '@/services/cashbox'
import type { CashDailySummary } from '../types'
import type { CashSession } from '@/types/cashbox'

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

// ─── Query key para sesión de caja ────────────────────────────────────────────

export const cashSessionKeys = {
  today: () => ['cash-session', 'today'] as const,
}

// ─── Esquemas de validacion de formularios ────────────────────────────────────

const openCashSchema = z.object({
  opening_amount: z
    .number({ invalid_type_error: 'Ingresá un monto válido.' })
    .min(0, 'El monto no puede ser negativo.'),
})

const closeCashSchema = z.object({
  closing_amount: z
    .number({ invalid_type_error: 'Ingresá un monto válido.' })
    .min(0, 'El monto no puede ser negativo.'),
  notes: z.string().optional(),
})

type OpenCashForm = z.infer<typeof openCashSchema>
type CloseCashForm = z.infer<typeof closeCashSchema>

// ─── Modal: Abrir caja ────────────────────────────────────────────────────────

interface OpenCashModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

function OpenCashModal({ isOpen, onClose, onSuccess }: OpenCashModalProps) {
  const queryClient = useQueryClient()
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<OpenCashForm>({
    resolver: zodResolver(openCashSchema),
    defaultValues: { opening_amount: 0 },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (data: OpenCashForm) =>
      openCashSession({ opening_amount: data.opening_amount }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cashSessionKeys.today() })
      reset()
      setApiError(null)
      onSuccess()
      onClose()
    },
    onError: (err) => {
      setApiError(extractApiErrorMessage(err))
    },
  })

  function handleClose() {
    reset()
    setApiError(null)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Abrir caja" size="sm">
      <form
        onSubmit={(e) => {
          void handleSubmit((data) => mutate(data))(e)
        }}
        className="space-y-4"
      >
        <div>
          <label
            htmlFor="opening_amount"
            className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
          >
            Monto inicial en caja
          </label>
          <input
            id="opening_amount"
            type="number"
            step="0.01"
            min="0"
            placeholder="0"
            {...register('opening_amount', { valueAsNumber: true })}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
          {errors.opening_amount && (
            <p className="mt-1 text-xs text-red-600">{errors.opening_amount.message}</p>
          )}
        </div>

        {apiError && (
          <p className="flex items-center gap-1.5 text-sm text-red-600">
            <AlertCircle size={15} aria-hidden="true" />
            {apiError}
          </p>
        )}

        <div className="flex gap-2 pt-1">
          <Button
            type="button"
            variant="secondary"
            fullWidth
            onClick={handleClose}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" variant="primary" fullWidth isLoading={isPending}>
            Abrir caja
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ─── Modal: Cerrar caja ───────────────────────────────────────────────────────

interface CloseCashModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

function CloseCashModal({ isOpen, onClose, onSuccess }: CloseCashModalProps) {
  const queryClient = useQueryClient()
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CloseCashForm>({
    resolver: zodResolver(closeCashSchema),
    defaultValues: { closing_amount: 0, notes: '' },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (data: CloseCashForm) =>
      closeCashSession({
        closing_amount: data.closing_amount,
        notes: data.notes || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cashSessionKeys.today() })
      reset()
      setApiError(null)
      onSuccess()
      onClose()
    },
    onError: (err) => {
      setApiError(extractApiErrorMessage(err))
    },
  })

  function handleClose() {
    reset()
    setApiError(null)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Cerrar caja" size="sm">
      <form
        onSubmit={(e) => {
          void handleSubmit((data) => mutate(data))(e)
        }}
        className="space-y-4"
      >
        <div>
          <label
            htmlFor="closing_amount"
            className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
          >
            Monto contado en caja
          </label>
          <input
            id="closing_amount"
            type="number"
            step="0.01"
            min="0"
            placeholder="0"
            {...register('closing_amount', { valueAsNumber: true })}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
          {errors.closing_amount && (
            <p className="mt-1 text-xs text-red-600">{errors.closing_amount.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="close_notes"
            className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
          >
            Notas <span className="text-gray-400 font-normal">(opcional)</span>
          </label>
          <textarea
            id="close_notes"
            rows={3}
            placeholder="Observaciones del cierre..."
            {...register('notes')}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
          />
        </div>

        {apiError && (
          <p className="flex items-center gap-1.5 text-sm text-red-600">
            <AlertCircle size={15} aria-hidden="true" />
            {apiError}
          </p>
        )}

        <div className="flex gap-2 pt-1">
          <Button
            type="button"
            variant="secondary"
            fullWidth
            onClick={handleClose}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" variant="danger" fullWidth isLoading={isPending}>
            Cerrar caja
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ─── Bloque de sesión de caja ─────────────────────────────────────────────────

interface CashSessionBlockProps {
  session: CashSession | null
  isLoading: boolean
  isError: boolean
  errorMsg: string
}

function CashSessionBlock({
  session,
  isLoading,
  isError,
  errorMsg,
}: CashSessionBlockProps) {
  const [openModal, setOpenModal] = useState<'open' | 'close' | null>(null)

  // Skeleton mientras carga
  if (isLoading) {
    return (
      <div
        aria-busy="true"
        aria-label="Cargando sesión de caja..."
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-4 animate-pulse space-y-2"
      >
        <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-3 w-48 rounded bg-gray-100 dark:bg-gray-750" />
      </div>
    )
  }

  // Error inline
  if (isError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800 px-4 py-3 flex items-center gap-2 text-sm text-red-700 dark:text-red-400">
        <AlertCircle size={16} aria-hidden="true" />
        <span>{errorMsg}</span>
      </div>
    )
  }

  // Sin sesión: caja cerrada, sin datos
  if (!session) {
    return (
      <>
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700 shrink-0">
              <Lock size={18} className="text-gray-500 dark:text-gray-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                Caja cerrada
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                No hay sesión abierta para hoy
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setOpenModal('open')}
            leftIcon={<LockOpen size={15} aria-hidden="true" />}
          >
            Abrir caja
          </Button>
        </div>

        <OpenCashModal
          isOpen={openModal === 'open'}
          onClose={() => setOpenModal(null)}
          onSuccess={() => { /* la invalidación la hace el modal */ }}
        />
      </>
    )
  }

  // Sesión OPEN
  if (session.status === 'OPEN') {
    return (
      <>
        <div className="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30 px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/40 shrink-0">
                <LockOpen size={18} className="text-green-600 dark:text-green-400" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-green-800 dark:text-green-300">
                  Caja abierta
                </p>
                <p className="text-xs text-green-700 dark:text-green-500 truncate">
                  Desde {formatDateTimeBA(session.opened_at)} &middot; Inicial{' '}
                  {formatARS(session.opening_amount)}
                </p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setOpenModal('close')}
              leftIcon={<Lock size={15} aria-hidden="true" />}
              className="shrink-0 border-green-300 dark:border-green-700 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-900/40"
            >
              Cerrar caja
            </Button>
          </div>
        </div>

        <CloseCashModal
          isOpen={openModal === 'close'}
          onClose={() => setOpenModal(null)}
          onSuccess={() => { /* la invalidación la hace el modal */ }}
        />
      </>
    )
  }

  // Sesión CLOSED
  const difference = session.difference ? parseFloat(session.difference) : null
  const diffIsNegative = difference !== null && difference < 0

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-4 space-y-3">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700 shrink-0">
          <Lock size={18} className="text-gray-500 dark:text-gray-400" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
            Caja cerrada
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Apertura: {formatDateTimeBA(session.opened_at)}
            {session.closed_at && (
              <> &middot; Cierre: {formatDateTimeBA(session.closed_at)}</>
            )}
          </p>
        </div>
      </div>

      {/* Resumen de montos */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg bg-gray-50 dark:bg-gray-700/50 px-3 py-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
            Monto inicial
          </p>
          <p className="font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
            {formatARS(session.opening_amount)}
          </p>
        </div>

        <div className="rounded-lg bg-gray-50 dark:bg-gray-700/50 px-3 py-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
            Monto contado
          </p>
          <p className="font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
            {session.closing_amount ? formatARS(session.closing_amount) : '—'}
          </p>
        </div>

        <div className="rounded-lg bg-gray-50 dark:bg-gray-700/50 px-3 py-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
            Esperado
          </p>
          <p className="font-semibold text-gray-900 dark:text-gray-100 mt-0.5">
            {session.expected_amount ? formatARS(session.expected_amount) : '—'}
          </p>
        </div>

        <div className="rounded-lg bg-gray-50 dark:bg-gray-700/50 px-3 py-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
            Diferencia
          </p>
          <p
            className={[
              'font-semibold mt-0.5 flex items-center gap-1',
              difference === null
                ? 'text-gray-400'
                : diffIsNegative
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-green-600 dark:text-green-400',
            ].join(' ')}
          >
            {difference === null ? (
              '—'
            ) : (
              <>
                {diffIsNegative && (
                  <AlertCircle size={13} aria-hidden="true" />
                )}
                {diffIsNegative ? '' : '+'}
                {formatARS(session.difference!)}
              </>
            )}
          </p>
        </div>
      </div>

      {/* Notas */}
      {session.notes && (
        <p className="text-xs text-gray-500 dark:text-gray-400 italic">
          {session.notes}
        </p>
      )}
    </div>
  )
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
      className="grid grid-cols-3 divide-x divide-gray-200 dark:divide-gray-700 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
    >
      {/* Ingresos */}
      <div className="px-4 py-3 text-center">
        <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
          Ingresos
        </p>
        {placeholder ? (
          <p className="text-base font-bold text-gray-400 mt-1">—</p>
        ) : (
          <p className="text-base font-bold text-green-600 mt-1">
            {formatARS(summary.ingresos)}
          </p>
        )}
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
          {placeholder
            ? '—'
            : `${summary.ingresos_count} movimiento${summary.ingresos_count !== 1 ? 's' : ''}`}
        </p>
      </div>

      {/* Devoluciones */}
      <div className="px-4 py-3 text-center">
        <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
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
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
          {placeholder
            ? '—'
            : `${summary.devoluciones_count} reversion${summary.devoluciones_count !== 1 ? 'es' : ''}`}
        </p>
      </div>

      {/* Total neto */}
      <div className="px-4 py-3 text-center">
        <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
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

  // Sesión de caja del dia actual (siempre "today", no filtrada por selectedDate)
  const {
    data: cashSession,
    isLoading: sessionLoading,
    isError: sessionError,
    error: sessionErrorObj,
  } = useQuery({
    queryKey: cashSessionKeys.today(),
    queryFn: getCashSessionToday,
  })

  async function handleExportCSV() {
    try {
      const response = await apiClient.get('/cash-movements/export/', {
        params: { date: selectedDate },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `caja_${selectedDate}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error al exportar CSV:', err)
    }
  }

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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          <Wallet size={20} className="text-brand-600" aria-hidden="true" />
          <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">Caja diaria</h1>
          <button
            type="button"
            onClick={() => void handleExportCSV()}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-brand-700 hover:bg-brand-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700 transition-colors"
          >
            <Download size={15} aria-hidden="true" />
            Exportar CSV
          </button>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-5 space-y-5">
        {/* Bloque de sesión de caja — siempre visible, refleja el dia actual */}
        <CashSessionBlock
          session={cashSession ?? null}
          isLoading={sessionLoading}
          isError={sessionError}
          errorMsg={extractApiErrorMessage(sessionErrorObj)}
        />

        {/* Selector de fecha */}
        <div className="space-y-1.5">
          <label
            htmlFor="cashbox-date"
            className="block text-sm font-medium text-gray-700 dark:text-gray-200"
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
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
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
                    className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-3 flex items-start justify-between gap-3"
                  >
                    {/* Info del movimiento */}
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {movement.booking_court}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatTimeBA(movement.created_at)} &middot; por{' '}
                        <span className="text-gray-600 dark:text-gray-300">
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
