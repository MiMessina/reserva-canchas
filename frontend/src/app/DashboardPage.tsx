/**
 * app/DashboardPage.tsx
 * ---------------------
 * Panel de inicio para operator/admin.
 * Muestra estadísticas del día: reservas, canchas ocupadas y caja.
 * Datos provistos por GET /api/dashboard/ — se refrescan cada 60 segundos.
 */

import { Link } from 'react-router-dom'
import {
  LayoutDashboard,
  CalendarCheck,
  Banknote,
  Layers,
} from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { ErrorState } from '@/components/ErrorState'
import { useDashboardSummary } from '@/features/booking/hooks/useBookings'
import { formatDateBA } from '@/lib/datetime'

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Formatea un decimal string de la API como moneda argentina. */
function formatARS(value: string | undefined): string {
  if (value === undefined) return '—'
  const num = parseFloat(value)
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

/** Fecha de hoy en Buenos Aires como texto largo: "lunes, 8 de junio de 2026". */
function todayLabelBA(): string {
  return formatDateBA(new Date())
}

// ─── Sub-componentes ──────────────────────────────────────────────────────────

interface StatCardProps {
  label: string
  value: number | string | undefined
  cardClass: string
  labelClass: string
  valueClass: string
}

function StatCard({ label, value, cardClass, labelClass, valueClass }: StatCardProps) {
  return (
    <div className={`rounded-xl p-4 border transition-colors ${cardClass}`}>
      <p className={`text-xs font-semibold uppercase tracking-wide mb-2 ${labelClass}`}>
        {label}
      </p>
      <p className={`text-3xl font-bold leading-none ${valueClass}`}>
        {value ?? '—'}
      </p>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function DashboardPage() {
  const { data, isLoading, isError, refetch } = useDashboardSummary()

  // Estado de carga: spinner centrado
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <Spinner size="lg" />
        <p className="text-sm text-gray-500">Cargando panel...</p>
      </div>
    )
  }

  // Estado de error: ErrorState con botón de reintento
  if (isError) {
    return (
      <ErrorState
        message="No se pudo cargar el panel. Verificá tu conexión e intentá de nuevo."
        onRetry={() => void refetch()}
        retryLabel="Reintentar"
      />
    )
  }

  // Métricas del día (con fallback a — cuando data aún no está disponible)
  const bt = data?.bookings_today
  const totalHoy = bt?.total ?? '—'
  const courtsOccupied = data?.courts_occupied_now ?? 0
  const courtsTotal = data?.courts_total ?? 0
  const occupancyRatio = courtsTotal > 0 ? courtsOccupied / courtsTotal : 0
  const occupancyPct = Math.round(occupancyRatio * 100)
  const occupancyBarColor =
    occupancyRatio >= 0.8 ? 'bg-orange-500' : 'bg-brand-600'

  const cashTotal = data?.cashbox_today?.total
  const cashIngresos = data?.cashbox_today?.ingresos
  const cashTotalNum = cashTotal !== undefined ? parseFloat(cashTotal) : 0
  const cashTotalNegative = !isNaN(cashTotalNum) && cashTotalNum < 0

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-8">

      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <span className="text-brand-600">
          <LayoutDashboard size={28} strokeWidth={1.8} aria-hidden="true" />
        </span>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 leading-tight">
            Panel de inicio
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
            {todayLabelBA()}
          </p>
        </div>
      </div>

      {/* ── Sección 1: Reservas de hoy ────────────────────────────────────── */}
      <section aria-labelledby="bookings-heading">
        <div className="flex items-center justify-between mb-3">
          <h2
            id="bookings-heading"
            className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide"
          >
            Reservas de hoy
          </h2>
          <span className="text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full px-2.5 py-0.5">
            {totalHoy} {totalHoy === 1 ? 'turno' : 'turnos'} hoy
          </span>
        </div>

        {/* Grid 2×2 en mobile, 4 columnas en md+ */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="Pendiente de seña"
            value={bt?.pending_payment}
            cardClass="bg-amber-500/10 border-amber-500/30 hover:bg-amber-500/20"
            labelClass="text-amber-500 dark:text-amber-400"
            valueClass="text-amber-600 dark:text-amber-300"
          />
          <StatCard
            label="Confirmadas"
            value={bt?.confirmed}
            cardClass="bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20"
            labelClass="text-emerald-600 dark:text-emerald-400"
            valueClass="text-emerald-700 dark:text-emerald-300"
          />
          <StatCard
            label="Completadas"
            value={bt?.completed}
            cardClass="bg-slate-500/10 border-slate-500/25 hover:bg-slate-500/20"
            labelClass="text-slate-500 dark:text-slate-400"
            valueClass="text-slate-600 dark:text-slate-300"
          />
          <StatCard
            label="Canceladas"
            value={bt?.cancelled}
            cardClass="bg-rose-500/10 border-rose-500/30 hover:bg-rose-500/20"
            labelClass="text-rose-500 dark:text-rose-400"
            valueClass="text-rose-600 dark:text-rose-300"
          />
        </div>
      </section>

      {/* ── Sección 2: Canchas y Caja ─────────────────────────────────────── */}
      <section aria-labelledby="status-heading">
        <h2
          id="status-heading"
          className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3"
        >
          Estado actual
        </h2>

        {/* Grid 1 col en mobile, 2 col en md+ */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* Tarjeta — Canchas */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 space-y-3">
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Layers size={18} strokeWidth={1.8} aria-hidden="true" />
              <span className="font-semibold text-sm">Canchas ocupadas ahora</span>
            </div>
            <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {data ? (
                <>
                  {courtsOccupied}
                  <span className="text-base font-normal text-gray-400 dark:text-gray-500 ml-1">
                    / {courtsTotal}
                  </span>
                </>
              ) : '—'}
            </p>
            {/* Barra de progreso */}
            <div
              className="w-full h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={occupancyPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${occupancyPct}% de canchas ocupadas`}
            >
              <div
                className={`h-full rounded-full transition-all duration-500 ${occupancyBarColor}`}
                style={{ width: `${occupancyPct}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {occupancyPct}% de ocupación
            </p>
          </div>

          {/* Tarjeta — Caja del día */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 space-y-2">
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
              <Banknote size={18} strokeWidth={1.8} aria-hidden="true" />
              <span className="font-semibold text-sm">Caja del día</span>
            </div>
            <p
              className={`text-3xl font-bold ${
                cashTotalNegative
                  ? 'text-red-500 dark:text-red-400'
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              {formatARS(cashTotal)}
            </p>
            <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
              Ingresos: {formatARS(cashIngresos)}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {data?.cashbox_today?.movements_count ?? 0} movimiento
              {(data?.cashbox_today?.movements_count ?? 0) !== 1 ? 's' : ''} registrado
              {(data?.cashbox_today?.movements_count ?? 0) !== 1 ? 's' : ''}
            </p>
          </div>

        </div>
      </section>

      {/* ── Quick links ───────────────────────────────────────────────────── */}
      <section aria-labelledby="quicklinks-heading">
        <h2
          id="quicklinks-heading"
          className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3"
        >
          Accesos rápidos
        </h2>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/admin/bookings"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <CalendarCheck size={16} aria-hidden="true" />
            Reservas
          </Link>
          <Link
            to="/admin/cashbox"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Banknote size={16} aria-hidden="true" />
            Caja diaria
          </Link>
          <Link
            to="/admin/courts"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Layers size={16} aria-hidden="true" />
            Canchas
          </Link>
        </div>
      </section>

    </div>
  )
}
