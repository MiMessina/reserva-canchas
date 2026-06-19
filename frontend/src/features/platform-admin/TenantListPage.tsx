/**
 * features/platform-admin/TenantListPage.tsx
 * --------------------------------------------
 * Página principal del panel de platform: lista de tenants.
 *
 * Columnas: Nombre, Schema, Dominio, Estado (badge), Fecha de alta.
 * Acciones por fila: toggle activo/inactivo (con confirmación).
 * Botón "Nuevo complejo" que abre TenantCreateModal.
 * Estados: loading skeleton, empty, error.
 * Mobile-first: tabla scrollable en horizontal en pantallas chicas.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, ToggleLeft, ToggleRight, ExternalLink, RefreshCw } from 'lucide-react'
import { usePlatformTenants, useToggleTenant } from './hooks/usePlatformTenants'
import { TenantCreateModal } from './TenantCreateModal'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { Spinner } from '@/components/Spinner'
import { formatTenantDate } from './platformDateHelper'
import type { Tenant } from './types'

// ─── Componente ───────────────────────────────────────────────────────────────

export function TenantListPage() {
  const { data: tenantsPage, isLoading, isError, refetch } = usePlatformTenants()
  const tenants = tenantsPage?.results ?? []
  const { mutate: toggleTenant, isPending: isToggling } = useToggleTenant()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [confirmToggleId, setConfirmToggleId] = useState<number | null>(null)

  // ─── Handlers ───────────────────────────────────────────────────────────────

  function handleToggleRequest(tenant: Tenant) {
    setConfirmToggleId(tenant.id)
  }

  function handleToggleConfirm() {
    if (confirmToggleId === null) return
    toggleTenant(confirmToggleId, {
      onSettled: () => setConfirmToggleId(null),
    })
  }

  function handleToggleCancel() {
    setConfirmToggleId(null)
  }

  // ─── States ──────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" label="Cargando complejos..." />
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState
        message="No se pudo cargar la lista de complejos."
        onRetry={() => void refetch()}
        retryLabel="Reintentar"
      />
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            Complejos registrados
          </h1>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
            {tenantsPage && tenantsPage.count > 0
              ? `${tenantsPage.count} complejo${tenantsPage.count === 1 ? '' : 's'} en la plataforma`
              : 'Sin complejos aún'}
          </p>
        </div>
        <Button
          leftIcon={<Plus size={16} />}
          onClick={() => setIsCreateModalOpen(true)}
          className="bg-gray-800 hover:bg-gray-900 text-white focus:ring-gray-700 shrink-0"
        >
          Nuevo complejo
        </Button>
      </div>

      {/* Lista vacía */}
      {tenants.length === 0 && (
        <EmptyState
          title="No hay complejos registrados"
          description="Creá el primer complejo para comenzar."
          action={
            <Button
              leftIcon={<Plus size={16} />}
              onClick={() => setIsCreateModalOpen(true)}
              className="bg-gray-800 hover:bg-gray-900 text-white focus:ring-gray-700"
            >
              Nuevo complejo
            </Button>
          }
        />
      )}

      {/* Tabla */}
      {tenants.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <Th>Nombre</Th>
                <Th>Schema</Th>
                <Th>Dominio</Th>
                <Th>Estado</Th>
                <Th>Alta</Th>
                <Th align="right">Acciones</Th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
              {tenants.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  {/* Nombre */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Link
                      to={`/tenants/${tenant.id}`}
                      className="text-sm font-medium text-gray-900 dark:text-gray-100 hover:underline"
                    >
                      {tenant.name}
                    </Link>
                  </td>

                  {/* Schema */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <code className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 rounded">
                      {tenant.schema_name}
                    </code>
                  </td>

                  {/* Dominio */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-1">
                      {tenant.domain}
                      <ExternalLink size={12} className="text-gray-400 shrink-0" aria-hidden="true" />
                    </span>
                  </td>

                  {/* Estado */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <StatusBadge isActive={tenant.is_active} />
                  </td>

                  {/* Fecha de alta */}
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {formatTenantDate(tenant.created_at)}
                  </td>

                  {/* Acciones */}
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/tenants/${tenant.id}`}
                        className="text-xs text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 underline"
                      >
                        Ver detalle
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleToggleRequest(tenant)}
                        disabled={isToggling && confirmToggleId === tenant.id}
                        aria-label={
                          tenant.is_active
                            ? `Desactivar ${tenant.name}`
                            : `Activar ${tenant.name}`
                        }
                        className={[
                          'flex items-center gap-1 text-xs px-2 py-1 rounded-md font-medium transition-colors',
                          'focus:outline-none focus:ring-2 focus:ring-offset-1',
                          tenant.is_active
                            ? 'text-red-600 hover:bg-red-50 focus:ring-red-400 dark:text-red-400 dark:hover:bg-red-900/20'
                            : 'text-green-600 hover:bg-green-50 focus:ring-green-400 dark:text-green-400 dark:hover:bg-green-900/20',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                        ].join(' ')}
                      >
                        {isToggling && confirmToggleId === tenant.id ? (
                          <Spinner size="sm" color="gray" />
                        ) : tenant.is_active ? (
                          <ToggleRight size={14} aria-hidden="true" />
                        ) : (
                          <ToggleLeft size={14} aria-hidden="true" />
                        )}
                        {tenant.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de creación */}
      <TenantCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      {/* Dialogo de confirmación de toggle */}
      {confirmToggleId !== null && (
        <ToggleConfirmDialog
          tenant={tenants.find((t) => t.id === confirmToggleId) ?? null}
          isLoading={isToggling}
          onConfirm={handleToggleConfirm}
          onCancel={handleToggleCancel}
        />
      )}
    </div>
  )
}

// ─── Sub-componentes ──────────────────────────────────────────────────────────

function Th({
  children,
  align = 'left',
}: {
  children: React.ReactNode
  align?: 'left' | 'right'
}) {
  return (
    <th
      scope="col"
      className={[
        'px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider',
        align === 'right' ? 'text-right' : 'text-left',
      ].join(' ')}
    >
      {children}
    </th>
  )
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
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

function ToggleConfirmDialog({
  tenant,
  isLoading,
  onConfirm,
  onCancel,
}: {
  tenant: Tenant | null
  isLoading: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  if (!tenant) return null

  const action = tenant.is_active ? 'desactivar' : 'activar'
  const actionLabel = tenant.is_active ? 'Desactivar' : 'Activar'

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-0 sm:px-4"
    >
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        aria-hidden="true"
        onClick={onCancel}
      />
      <div className="relative z-10 w-full sm:max-w-sm bg-white dark:bg-gray-800 rounded-t-2xl sm:rounded-2xl shadow-xl p-6">
        <h2
          id="confirm-title"
          className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2"
        >
          Confirmar {action}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          ¿Querés {action} el complejo <strong>{tenant.name}</strong>?
          {tenant.is_active &&
            ' Los usuarios de este tenant no podrán loguearse mientras esté inactivo.'}
        </p>
        <div className="flex flex-col-reverse sm:flex-row gap-3 sm:justify-end">
          <Button variant="secondary" onClick={onCancel} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            variant={tenant.is_active ? 'danger' : 'primary'}
            isLoading={isLoading}
            onClick={onConfirm}
            leftIcon={
              isLoading ? undefined : tenant.is_active ? (
                <ToggleRight size={16} />
              ) : (
                <ToggleLeft size={16} />
              )
            }
          >
            {isLoading ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                Procesando...
              </>
            ) : (
              actionLabel
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
