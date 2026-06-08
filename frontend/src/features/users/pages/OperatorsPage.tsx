/**
 * features/users/pages/OperatorsPage.tsx
 * ----------------------------------------
 * Gestion de operadores del complejo. Ruta: /admin/operators (tenant_admin).
 *
 * Funcionalidad:
 *  - Lista de operadores activos: email, nombre completo, fecha de alta.
 *  - Boton "Nuevo operador" que abre un modal de creacion inline.
 *  - Boton "Dar de baja" por operador: pide confirmacion con window.confirm.
 *  - Estados loading / empty / error.
 */

import { useState } from 'react'
import { UserPlus, Trash2, Users } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { useOperators, useCreateOperator, useDeleteOperator } from '../hooks/useOperators'
import { extractApiErrorMessage } from '@/lib/apiError'
import { formatDateBA } from '@/lib/datetime'
import type { CreateOperatorPayload } from '../types'

// ─── Modal de creacion ────────────────────────────────────────────────────────

interface CreateOperatorModalProps {
  onClose: () => void
}

function CreateOperatorModal({ onClose }: CreateOperatorModalProps) {
  const [form, setForm] = useState<CreateOperatorPayload>({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
  })
  const [apiError, setApiError] = useState<string | null>(null)
  const createOperator = useCreateOperator()

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setApiError(null)
    try {
      await createOperator.mutateAsync(form)
      onClose()
    } catch (err) {
      setApiError(extractApiErrorMessage(err))
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-5 space-y-4">
        <h2 className="font-semibold text-gray-900">Nuevo operador</h2>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
          <div className="space-y-1">
            <label
              htmlFor="op-first-name"
              className="block text-sm font-medium text-gray-700"
            >
              Nombre
            </label>
            <input
              id="op-first-name"
              name="first_name"
              type="text"
              required
              value={form.first_name}
              onChange={handleChange}
              placeholder="Ej: Juan"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="op-last-name"
              className="block text-sm font-medium text-gray-700"
            >
              Apellido
            </label>
            <input
              id="op-last-name"
              name="last_name"
              type="text"
              required
              value={form.last_name}
              onChange={handleChange}
              placeholder="Ej: Perez"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="op-email"
              className="block text-sm font-medium text-gray-700"
            >
              Email
            </label>
            <input
              id="op-email"
              name="email"
              type="email"
              required
              value={form.email}
              onChange={handleChange}
              placeholder="operador@complejo.com"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="op-password"
              className="block text-sm font-medium text-gray-700"
            >
              Contrasena
            </label>
            <input
              id="op-password"
              name="password"
              type="password"
              required
              value={form.password}
              onChange={handleChange}
              placeholder="Minimo 8 caracteres"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          {apiError && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700"
            >
              {apiError}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createOperator.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
            >
              {createOperator.isPending ? (
                <Spinner size="sm" color="white" label="Creando..." />
              ) : null}
              Crear operador
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function OperatorsPage() {
  const [isCreating, setIsCreating] = useState(false)
  const { data, isLoading, isError, error, refetch } = useOperators()
  const deleteOperator = useDeleteOperator()

  const operators = data?.results ?? []

  async function handleDelete(id: number, email: string) {
    const confirmed = window.confirm(
      `¿Dar de baja al operador ${email}? Esta accion no se puede deshacer.`,
    )
    if (!confirmed) return
    try {
      await deleteOperator.mutateAsync(id)
    } catch (err) {
      console.error('Error al dar de baja al operador:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center gap-2">
          <Users size={20} className="text-brand-600" aria-hidden="true" />
          <h1 className="text-base font-semibold text-gray-900">Operadores</h1>
          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 transition-colors"
          >
            <UserPlus size={15} aria-hidden="true" />
            Nuevo operador
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-5 space-y-4">
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando operadores..." />
          </div>
        )}

        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {!isLoading && !isError && operators.length === 0 && (
          <EmptyState
            icon={<Users size={48} strokeWidth={1.5} />}
            title="Sin operadores"
            description="No hay operadores registrados. Crea uno con el boton de arriba."
          />
        )}

        {!isLoading && !isError && operators.length > 0 && (
          <ul className="space-y-2" aria-label="Lista de operadores">
            {operators.map((operator) => (
              <li
                key={operator.id}
                className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center justify-between gap-3"
              >
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {operator.first_name} {operator.last_name}
                  </p>
                  <p className="text-xs text-gray-500 truncate">{operator.email}</p>
                  <p className="text-xs text-gray-400">
                    Alta: {formatDateBA(operator.created_at)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDelete(operator.id, operator.email)}
                  disabled={deleteOperator.isPending}
                  aria-label={`Dar de baja a ${operator.email}`}
                  title="Dar de baja"
                  className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-red-600 hover:text-red-800 hover:bg-red-50 border border-transparent hover:border-red-200 disabled:opacity-40 transition-colors"
                >
                  <Trash2 size={14} aria-hidden="true" />
                  Dar de baja
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>

      {isCreating && <CreateOperatorModal onClose={() => setIsCreating(false)} />}
    </div>
  )
}
