/**
 * features/reports/ReportsPage.tsx
 * ----------------------------------
 * Página de reportes semanales. Ruta: /admin/reports (requiere JWT).
 *
 * Layout:
 *  - Header con título + selector de rango de fechas (lunes-domingo de la semana actual por defecto).
 *  - Botón "Ver reporte" que dispara el fetch.
 *  - Sección Resumen: 4 tarjetas de totales.
 *  - Tabla "Por día": reservas y revenue por día de la semana.
 *  - Tabla "Por cancha": ocupación y revenue por cancha.
 *
 * Estados: loading · empty · error.
 * Mobile-first, dark mode incluido.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, CalendarRange, Search } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { getWeeklyReport } from '@/services/reportsService'
import { formatCurrency, formatDayLabel } from '@/lib/formatters'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { WeeklyReport } from '@/types/reports'

// ─── Helpers de rango de semana ───────────────────────────────────────────────

/** Devuelve {dateFrom, dateTo} del lunes al domingo de la semana actual (en hora local). */
function currentWeekRange(): { dateFrom: string; dateTo: string } {
  const today = new Date()
  const dayOfWeek = today.getDay() // 0=domingo, 1=lunes...
  const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek

  const monday = new Date(today)
  monday.setDate(today.getDate() + diffToMonday)
  monday.setHours(0, 0, 0, 0)

  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)

  const toYMD = (d: Date) => d.toISOString().slice(0, 10)
  return { dateFrom: toYMD(monday), dateTo: toYMD(sunday) }
}

// ─── Tipos de display de tipo de cancha ───────────────────────────────────────

const COURT_TYPE_LABELS: Record<string, string> = {
  FUTBOL5: 'Fútbol 5',
  FUTBOL7: 'Fútbol 7',
  PADEL: 'Pádel',
}

function courtTypeLabel(type: string): string {
  return COURT_TYPE_LABELS[type] ?? type
}

// ─── Sub-componente: tarjeta de resumen ───────────────────────────────────────

interface SummaryCardProps {
  label: string
  value: string | number
  colorClasses: string
}

function SummaryCard({ label, value, colorClasses }: SummaryCardProps) {
  return (
    <div className={`rounded-xl p-4 ${colorClasses}`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70 mb-1">
        {label}
      </p>
      <p className="text-2xl font-bold leading-none">{value}</p>
    </div>
  )
}

// ─── Sub-componente: barra de progreso de ocupación ──────────────────────────

function OccupancyBar({ pct }: { pct: number }) {
  const clamped = Math.min(Math.max(pct, 0), 100)
  const barColor =
    clamped >= 80
      ? 'bg-orange-500'
      : clamped >= 50
        ? 'bg-brand-500'
        : 'bg-green-500'

  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div
        className="flex-1 h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${clamped.toFixed(1)}% de ocupación`}
      >
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs text-gray-600 dark:text-gray-400 shrink-0 w-10 text-right">
        {clamped.toFixed(1)}%
      </span>
    </div>
  )
}

// ─── Sub-componente: sección de resultados ────────────────────────────────────

function ReportResults({ report }: { report: WeeklyReport }) {
  const { totals, by_day, by_court } = report

  const confirmedAndCompleted = totals.confirmed + totals.completed

  return (
    <div className="space-y-8">
      {/* ── Resumen ──────────────────────────────────────────────────────── */}
      <section aria-labelledby="summary-heading">
        <h2
          id="summary-heading"
          className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3"
        >
          Resumen del período
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard
            label="Total reservas"
            value={totals.bookings_total}
            colorClasses="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
          />
          <SummaryCard
            label="Confirmadas + Completadas"
            value={confirmedAndCompleted}
            colorClasses="bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
          />
          <SummaryCard
            label="Canceladas"
            value={totals.cancelled}
            colorClasses="bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
          />
          <SummaryCard
            label="Ingresos confirmados"
            value={formatCurrency(totals.revenue_confirmed)}
            colorClasses="bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
          />
        </div>
      </section>

      {/* ── Por día ──────────────────────────────────────────────────────── */}
      <section aria-labelledby="by-day-heading">
        <h2
          id="by-day-heading"
          className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3"
        >
          Por día
        </h2>
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Fecha
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Total
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Confirmadas
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Completadas
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Canceladas
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Pendientes
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Ingresos
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-800">
              {by_day.map((row) => (
                <tr
                  key={row.date}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100 capitalize whitespace-nowrap">
                    {formatDayLabel(row.date)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {row.bookings_total}
                  </td>
                  <td className="px-4 py-3 text-right text-green-700 dark:text-green-400">
                    {row.confirmed}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500 dark:text-gray-400">
                    {row.completed}
                  </td>
                  <td className="px-4 py-3 text-right text-red-600 dark:text-red-400">
                    {row.cancelled}
                  </td>
                  <td className="px-4 py-3 text-right text-yellow-600 dark:text-yellow-400">
                    {row.pending_payment}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {formatCurrency(row.revenue_confirmed)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Por cancha ───────────────────────────────────────────────────── */}
      <section aria-labelledby="by-court-heading">
        <h2
          id="by-court-heading"
          className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3"
        >
          Por cancha
        </h2>
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Cancha
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Tipo
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Total
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Conf.+Comp.
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide min-w-[140px]">
                  % Ocupación
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Ingresos
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-800">
              {by_court.map((row) => (
                <tr
                  key={row.court_id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                    {row.court_name}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {courtTypeLabel(row.court_type)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {row.bookings_total}
                  </td>
                  <td className="px-4 py-3 text-right text-green-700 dark:text-green-400">
                    {row.confirmed_or_completed}
                  </td>
                  <td className="px-4 py-3">
                    <OccupancyBar pct={row.occupancy_pct} />
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {formatCurrency(row.revenue_confirmed)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function ReportsPage() {
  const { dateFrom: defaultFrom, dateTo: defaultTo } = currentWeekRange()

  const [dateFrom, setDateFrom] = useState<string>(defaultFrom)
  const [dateTo, setDateTo] = useState<string>(defaultTo)
  // Rango "activo" que efectivamente se le pasa a la query.
  // Se actualiza solo al hacer click en "Ver reporte" para evitar fetches
  // intermedios mientras el usuario tipea las fechas.
  const [activeRange, setActiveRange] = useState<{ from: string; to: string }>({
    from: defaultFrom,
    to: defaultTo,
  })

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['weekly-report', activeRange.from, activeRange.to],
    queryFn: () => getWeeklyReport(activeRange.from, activeRange.to),
    enabled: activeRange.from.length === 10 && activeRange.to.length === 10,
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (dateFrom.length === 10 && dateTo.length === 10) {
      setActiveRange({ from: dateFrom, to: dateTo })
    }
  }

  const isEmpty = !isLoading && !isError && data && data.totals.bookings_total === 0

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center gap-2 flex-wrap">
          <BarChart2 size={20} className="text-brand-600" aria-hidden="true" />
          <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">Reportes</h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-5 space-y-6">
        {/* ── Filtros ──────────────────────────────────────────────────────── */}
        <form
          onSubmit={handleSubmit}
          className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
          aria-label="Filtros de reporte semanal"
        >
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 shrink-0">
              <CalendarRange size={16} aria-hidden="true" />
              <span className="text-sm font-medium">Período</span>
            </div>
            <div className="flex flex-wrap gap-3 flex-1">
              <div className="flex flex-col gap-1">
                <label
                  htmlFor="date-from"
                  className="text-xs text-gray-500 dark:text-gray-400 font-medium"
                >
                  Desde
                </label>
                <input
                  id="date-from"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label
                  htmlFor="date-to"
                  className="text-xs text-gray-500 dark:text-gray-400 font-medium"
                >
                  Hasta
                </label>
                <input
                  id="date-to"
                  type="date"
                  value={dateTo}
                  min={dateFrom}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                />
              </div>
            </div>
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors disabled:opacity-50"
              disabled={isLoading}
            >
              <Search size={15} aria-hidden="true" />
              Ver reporte
            </button>
          </div>
        </form>

        {/* ── Estados ──────────────────────────────────────────────────────── */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando reporte..." />
          </div>
        )}

        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {isEmpty && (
          <EmptyState
            icon={<BarChart2 size={48} strokeWidth={1.5} />}
            title="Sin datos para el período"
            description="No hay reservas registradas en el rango de fechas seleccionado."
          />
        )}

        {/* ── Resultados ───────────────────────────────────────────────────── */}
        {!isLoading && !isError && data && !isEmpty && (
          <ReportResults report={data} />
        )}
      </main>
    </div>
  )
}
