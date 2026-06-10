import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, LayoutList } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { Button } from '@/components/Button'
import { Modal } from '@/components/Modal'
import { CourtCard } from '../components/CourtCard'
import { CourtForm } from '../components/CourtForm'
import { useCourts, useUpdateCourt } from '../hooks/useCourts'
import { useAuth } from '@/features/auth/useAuth'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { Court } from '../types'

export function CourtsListPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [showInactive, setShowInactive] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingCourt, setEditingCourt] = useState<Court | null>(null)

  const isTenantAdmin = user?.role === 'tenant_admin'

  const filters = showInactive ? undefined : { is_active: true }
  const { data, isLoading, isError, error, refetch } = useCourts(filters)
  const updateCourt = useUpdateCourt()

  const courts = data?.results ?? []

  function handleEdit(court: Court) {
    setEditingCourt(court)
  }

  function handleToggleActive(court: Court) {
    updateCourt.mutate({
      id: court.id,
      payload: { is_active: !court.is_active },
    })
  }

  function handleViewDetail(court: Court) {
    navigate(`/admin/courts/${court.id}`)
  }

  function handleCreateSuccess() {
    setShowCreateModal(false)
  }

  function handleEditSuccess() {
    setEditingCourt(null)
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-sm" aria-hidden="true">C</span>
          </div>
          <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">Canchas</h1>
        </div>

        {isTenantAdmin && (
          <Button
            size="sm"
            leftIcon={<Plus size={16} />}
            onClick={() => setShowCreateModal(true)}
          >
            Nueva cancha
          </Button>
        )}
      </header>

      <main className="max-w-lg mx-auto px-4 py-5 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {isLoading
              ? 'Cargando...'
              : `${courts.length} cancha${courts.length !== 1 ? 's' : ''}`}
          </span>
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <span className="text-sm text-gray-600 dark:text-gray-300">Mostrar inactivas</span>
            <button
              type="button"
              role="switch"
              aria-checked={showInactive}
              aria-label="Mostrar canchas inactivas"
              onClick={() => setShowInactive((v) => !v)}
              className={[
                'relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent',
                'transition-colors duration-200 ease-in-out',
                'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1',
                showInactive ? 'bg-brand-600' : 'bg-gray-300',
              ].join(' ')}
            >
              <span
                aria-hidden="true"
                className={[
                  'pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow',
                  'transform transition duration-200 ease-in-out',
                  showInactive ? 'translate-x-4' : 'translate-x-0',
                ].join(' ')}
              />
            </button>
          </label>
        </div>

        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" label="Cargando canchas..." />
          </div>
        )}

        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {!isLoading && !isError && courts.length === 0 && (
          <EmptyState
            icon={<LayoutList size={48} strokeWidth={1.5} />}
            title="No hay canchas"
            description={
              showInactive
                ? 'Todavia no hay canchas registradas.'
                : 'No hay canchas activas. Activa "Mostrar inactivas" para verlas todas.'
            }
            action={
              isTenantAdmin ? (
                <Button
                  size="sm"
                  leftIcon={<Plus size={16} />}
                  onClick={() => setShowCreateModal(true)}
                >
                  Crear primera cancha
                </Button>
              ) : undefined
            }
          />
        )}

        {!isLoading && !isError && courts.length > 0 && (
          <ul className="space-y-3" aria-label="Lista de canchas">
            {courts.map((court) => (
              <li key={court.id}>
                <CourtCard
                  court={court}
                  canEdit={isTenantAdmin}
                  onEdit={handleEdit}
                  onToggleActive={handleToggleActive}
                  onViewDetail={handleViewDetail}
                />
              </li>
            ))}
          </ul>
        )}
      </main>

      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Nueva cancha"
      >
        <CourtForm
          onSuccess={handleCreateSuccess}
          onCancel={() => setShowCreateModal(false)}
        />
      </Modal>

      <Modal
        isOpen={editingCourt !== null}
        onClose={() => setEditingCourt(null)}
        title="Editar cancha"
      >
        {editingCourt && (
          <CourtForm
            court={editingCourt}
            onSuccess={handleEditSuccess}
            onCancel={() => setEditingCourt(null)}
          />
        )}
      </Modal>
    </div>
  )
}
