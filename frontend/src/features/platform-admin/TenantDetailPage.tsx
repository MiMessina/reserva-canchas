/**
 * features/platform-admin/TenantDetailPage.tsx
 * ----------------------------------------------
 * Vista de detalle de un tenant del panel de platform.
 * Muestra todos los campos del tenant y permite toggle de estado.
 * Ruta: /tenants/:id
 */

import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, FlaskConical, Radio, ToggleLeft, ToggleRight } from 'lucide-react'
import { usePlatformTenant, useToggleTenant, useUpdateTenant } from './hooks/usePlatformTenants'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { Spinner } from '@/components/Spinner'
import { formatTenantDateTime } from './platformDateHelper'
import type { BotMode } from './types'

export function TenantDetailPage() {
  const { id } = useParams<{ id: string }>()
  const tenantId = Number(id)
  const { data: tenant, isLoading, isError, refetch } = usePlatformTenant(tenantId)
  const { mutate: toggleTenant, isPending: isToggling } = useToggleTenant()
  const { mutate: updateTenant, isPending: isUpdatingBotMode } = useUpdateTenant()

  function handleBotModeToggle(newMode: BotMode) {
    updateTenant({ id: tenantId, payload: { bot_mode: newMode } })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" label="Cargando complejo..." />
      </div>
    )
  }

  if (isError || !tenant) {
    return (
      <ErrorState
        message="No se pudo cargar el detalle del complejo."
        onRetry={() => void refetch()}
      />
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 sm:px-6">
      {/* Back */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 mb-6"
      >
        <ArrowLeft size={16} aria-hidden="true" />
        Volver a la lista
      </Link>

      {/* Card */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              {tenant.name}
            </h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              ID #{tenant.id}
            </p>
          </div>
          <StatusBadge isActive={tenant.is_active} />
        </div>

        {/* Campos */}
        <dl className="px-6 py-5 space-y-4">
          <Field label="Nombre" value={tenant.name} />
          <Field
            label="Schema (identificador técnico)"
            value={
              <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded">
                {tenant.schema_name}
              </code>
            }
          />
          <Field label="Dominio" value={tenant.domain} />
          <Field
            label="Estado"
            value={
              <StatusBadge isActive={tenant.is_active} />
            }
          />
          <Field
            label="Fecha de alta"
            value={formatTenantDateTime(tenant.created_at)}
          />
          <Field
            label="Modo del bot"
            value={<BotModeBadge mode={tenant.bot_mode} />}
          />
        </dl>

        {/* Acciones */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/40 border-t border-gray-100 dark:border-gray-700 flex flex-col sm:flex-row gap-3 sm:justify-end">
          {/* Toggle bot_mode */}
          <Button
            variant="secondary"
            isLoading={isUpdatingBotMode}
            leftIcon={
              tenant.bot_mode === 'mock' ? (
                <Radio size={16} />
              ) : (
                <FlaskConical size={16} />
              )
            }
            onClick={() =>
              handleBotModeToggle(tenant.bot_mode === 'mock' ? 'production' : 'mock')
            }
          >
            {tenant.bot_mode === 'mock' ? 'Pasar a Producción' : 'Pasar a Demo'}
          </Button>

          {/* Toggle is_active */}
          <Button
            variant={tenant.is_active ? 'danger' : 'secondary'}
            isLoading={isToggling}
            leftIcon={
              tenant.is_active ? (
                <ToggleRight size={16} />
              ) : (
                <ToggleLeft size={16} />
              )
            }
            onClick={() => toggleTenant(tenantId)}
          >
            {tenant.is_active ? 'Desactivar complejo' : 'Activar complejo'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Sub-componentes ──────────────────────────────────────────────────────────

function Field({
  label,
  value,
}: {
  label: string
  value: React.ReactNode
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:gap-6">
      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 w-48 shrink-0 mb-0.5 sm:mb-0">
        {label}
      </dt>
      <dd className="text-sm text-gray-900 dark:text-gray-100">{value}</dd>
    </div>
  )
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
        isActive
          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
          : 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
      ].join(' ')}
    >
      <span
        className={[
          'w-1.5 h-1.5 rounded-full',
          isActive ? 'bg-green-500' : 'bg-red-500',
        ].join(' ')}
        aria-hidden="true"
      />
      {isActive ? 'Activo' : 'Inactivo'}
    </span>
  )
}

function BotModeBadge({ mode }: { mode: BotMode }) {
  const isMock = mode === 'mock'
  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
        isMock
          ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
          : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      ].join(' ')}
    >
      {isMock ? <FlaskConical size={11} aria-hidden="true" /> : <Radio size={11} aria-hidden="true" />}
      {isMock ? 'Demo (conversaciones seed)' : 'Producción (bot real)'}
    </span>
  )
}
