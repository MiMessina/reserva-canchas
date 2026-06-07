/**
 * features/courts/components/ScheduleBlocksSection.tsx
 * ------------------------------------------------------
 * Seccion de bloques horarios dentro del detalle de una cancha.
 * Muestra la lista de bloques, permite agregar, editar y desactivar.
 * Solo visible/editable para tenant_admin.
 *
 * IMPORTANTE: open_time/close_time son horas de pared — NO se convierten timezone.
 */

import { useState } from 'react'
import { Plus, Pencil, Trash2, Clock } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { Button } from '@/components/Button'
import { Modal } from '@/components/Modal'
import { ScheduleBlockForm } from './ScheduleBlockForm'
import { useScheduleBlocks, useDeleteScheduleBlock } from '../hooks/useCourts'
import { WEEKDAY_LABELS } from '../types'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { ScheduleBlock, Weekday } from '../types'

interface ScheduleBlocksSectionProps {
  courtId: number
  canEdit: boolean
}

export function ScheduleBlocksSection({ courtId, canEdit }: ScheduleBlocksSectionProps) {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingBlock, setEditingBlock] = useState<ScheduleBlock | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch } = useScheduleBlocks(courtId)
  const deleteMutation = useDeleteScheduleBlock()

  const blocks = data?.results ?? []

  const handleDelete = (block: ScheduleBlock) => {
    if (!confirm(`Desactivar el bloque del ${WEEKDAY_LABELS[block.weekday as Weekday]}?`)) return
    setDeleteError(null)
    deleteMutation.mutate(
      { id: block.id, courtId },
      {
        onError: (err) => setDeleteError(extractApiErrorMessage(err)),
      },
    )
  }

  // Estado: cargando
  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner label="Cargando horarios..." />
      </div>
    )
  }

  // Estado: error
  if (isError) {
    return (
      <ErrorState
        message={extractApiErrorMessage(error)}
        onRetry={() => void refetch()}
      />
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Horarios
        </h3>
        {canEdit && (
          <Button
            size="sm"
            variant="secondary"
            leftIcon={<Plus size={14} />}
            onClick={() => setShowCreateModal(true)}
          >
            Agregar
          </Button>
        )}
      </div>

      {/* Error de eliminacion */}
      {deleteError && (
        <div role="alert" className="mb-3">
          <ErrorState message={deleteError} compact />
        </div>
      )}

      {/* Estado vacio */}
      {blocks.length === 0 ? (
        <EmptyState
          title="Sin horarios configurados"
          description="Agrega bloques horarios para habilitar la disponibilidad de esta cancha."
          icon={<Clock size={40} strokeWidth={1.5} />}
          action={
            canEdit ? (
              <Button
                size="sm"
                leftIcon={<Plus size={14} />}
                onClick={() => setShowCreateModal(true)}
              >
                Agregar horario
              </Button>
            ) : undefined
          }
        />
      ) : (
        <ul className="space-y-2" role="list" aria-label="Bloques horarios">
          {blocks.map((block) => (
            <li
              key={block.id}
              className={[
                'flex items-center justify-between rounded-xl border px-4 py-3',
                block.is_active
                  ? 'bg-white border-gray-200'
                  : 'bg-gray-50 border-gray-200 opacity-60',
              ].join(' ')}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Clock
                  size={16}
                  className="shrink-0 text-brand-500"
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <span className="block text-sm font-medium text-gray-800">
                    {WEEKDAY_LABELS[block.weekday as Weekday]}
                  </span>
                  <span className="block text-xs text-gray-500">
                    {block.open_time.slice(0, 5)} - {block.close_time.slice(0, 5)}
                  </span>
                </div>
                {!block.is_active && (
                  <span className="shrink-0 text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full">
                    inactivo
                  </span>
                )}
              </div>

              {canEdit && (
                <div className="flex gap-1 shrink-0 ml-2">
                  <button
                    type="button"
                    aria-label={`Editar bloque del ${WEEKDAY_LABELS[block.weekday as Weekday]}`}
                    onClick={() => setEditingBlock(block)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    aria-label={`Eliminar bloque del ${WEEKDAY_LABELS[block.weekday as Weekday]}`}
                    onClick={() => handleDelete(block)}
                    disabled={deleteMutation.isPending}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Modal: nuevo bloque */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Agregar horario"
        size="sm"
      >
        <ScheduleBlockForm
          courtId={courtId}
          onSuccess={() => setShowCreateModal(false)}
          onCancel={() => setShowCreateModal(false)}
        />
      </Modal>

      {/* Modal: editar bloque */}
      <Modal
        isOpen={editingBlock != null}
        onClose={() => setEditingBlock(null)}
        title="Editar horario"
        size="sm"
      >
        {editingBlock && (
          <ScheduleBlockForm
            courtId={courtId}
            block={editingBlock}
            onSuccess={() => setEditingBlock(null)}
            onCancel={() => setEditingBlock(null)}
          />
        )}
      </Modal>
    </div>
  )
}
