/**
 * features/courts/pages/CourtDetailPage.tsx
 * -------------------------------------------
 * Pantalla de detalle de una cancha.
 * Muestra los datos de la cancha y la seccion de horarios (ScheduleBlocks).
 * Accesible desde /admin/courts/:id
 *
 * Permisos: visible para todos los autenticados; edicion solo para tenant_admin.
 */

import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil, MapPin } from 'lucide-react'
import { useState } from 'react'
import { Spinner } from '@/components/Spinner'
import { ErrorState } from '@/components/ErrorState'
import { Button } from '@/components/Button'
import { Modal } from '@/components/Modal'
import { CourtForm } from '../components/CourtForm'
import { ScheduleBlocksSection } from '../components/ScheduleBlocksSection'
import { useCourt } from '../hooks/useCourts'
import { useAuth } from '@/features/auth/useAuth'
import { COURT_TYPE_LABELS } from '../types'
import { extractApiErrorMessage } from '@/lib/apiError'

function formatPrice(price: string): string {
  const num = parseFloat(price)
  if (isNaN(num)) return price
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(num)
}

export function CourtDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [showEditModal, setShowEditModal] = useState(false)

  const courtId = Number(id)
  const { data: court, isLoading, isError, error, refetch } = useCourt(courtId)

  const isTenantAdmin = user?.role === 'tenant_admin'

  if (isNaN(courtId) || courtId <= 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <ErrorState message="ID de cancha invalido." />
        <Button
          variant="secondary"
          size="sm"
          leftIcon={<ArrowLeft size={14} />}
          onClick={() => navigate('/admin/courts')}
          className="mt-4"
        >
          Volver a canchas
        </Button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
        <button
          type="button"
          aria-label="Volver al listado"
          onClick={() => navigate('/admin/courts')}
          className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-base font-semibold text-gray-900 flex-1 truncate">
          {isLoading ? 'Cargando...' : (court?.name ?? 'Detalle de cancha')}
        </h1>
        {isTenantAdmin && court && (
          <Button
            size="sm"
            variant="secondary"
            leftIcon={<Pencil size={14} />}
            onClick={() => setShowEditModal(true)}
          >
            Editar
          </Button>
        )}
      </header>

      <main className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* Estado: cargando */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <Spinner size="lg" label="Cargando cancha..." />
          </div>
        )}

        {/* Estado: error */}
        {isError && !isLoading && (
          <ErrorState
            message={extractApiErrorMessage(error)}
            onRetry={() => void refetch()}
          />
        )}

        {/* Datos de la cancha */}
        {court && !isLoading && (
          <>
            {/* Tarjeta de info */}
            <section
              aria-label="Informacion de la cancha"
              className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{court.name}</h2>
                  <div className="flex items-center gap-1.5 mt-1">
                    <MapPin size={13} className="text-gray-400" aria-hidden="true" />
                    <span className="text-sm text-gray-500">
                      {COURT_TYPE_LABELS[court.court_type]}
                      {court.surface ? ` · ${court.surface}` : ''}
                    </span>
                  </div>
                </div>
                <span
                  className={[
                    'shrink-0 inline-block px-2.5 py-1 rounded-full text-xs font-medium',
                    court.is_active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500',
                  ].join(' ')}
                >
                  {court.is_active ? 'Activa' : 'Inactiva'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-xl px-4 py-3">
                  <span className="block text-xs text-gray-400 mb-0.5">Precio base</span>
                  <span className="text-base font-bold text-gray-800">
                    {formatPrice(court.base_price)}
                  </span>
                </div>
                <div className="bg-gray-50 rounded-xl px-4 py-3">
                  <span className="block text-xs text-gray-400 mb-0.5">Duracion del turno</span>
                  <span className="text-base font-bold text-gray-800">
                    {court.slot_duration_minutes} min
                  </span>
                </div>
              </div>
            </section>

            {/* Seccion de horarios */}
            <section
              aria-label="Horarios de la cancha"
              className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5"
            >
              <ScheduleBlocksSection
                courtId={court.id}
                canEdit={isTenantAdmin}
              />
            </section>
          </>
        )}
      </main>

      {/* Modal: editar cancha */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Editar cancha"
      >
        {court && (
          <CourtForm
            court={court}
            onSuccess={() => setShowEditModal(false)}
            onCancel={() => setShowEditModal(false)}
          />
        )}
      </Modal>
    </div>
  )
}
