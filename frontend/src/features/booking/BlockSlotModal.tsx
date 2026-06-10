/**
 * features/booking/BlockSlotModal.tsx
 * -------------------------------------
 * Modal para bloquear o desbloquear un slot de la grilla admin.
 *
 * Modo 'block':   slot AVAILABLE → POST /api/slot-blocks/
 * Modo 'unblock': slot BLOCKED   → DELETE /api/slot-blocks/{block_id}/
 *
 * Al completar la acción llama onSuccess() para que el padre invalide
 * la query de la grilla.
 */

import { useState } from 'react'
import { Lock, Unlock, AlertTriangle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '@/components/Modal'
import { Button } from '@/components/Button'
import { formatTimeBA } from '@/lib/datetime'
import { extractApiErrorMessage } from '@/lib/apiError'
import { createSlotBlock, deleteSlotBlock } from '@/services/slotBlockService'
import { dailyGridKeys } from './hooks/useBookings'
import type { DailyGridSlot } from './types'

// ─── Props ────────────────────────────────────────────────────────────────────

interface BlockSlotModalProps {
  /** Slot sobre el que se actúa. null = modal cerrado. */
  slot: DailyGridSlot | null
  /** ID de la cancha a la que pertenece el slot. */
  courtId: number | null
  /** Fecha seleccionada en la grilla (YYYY-MM-DD), para invalidar la query correcta. */
  selectedDate: string
  onClose: () => void
  onSuccess: () => void
}

// ─── Componente ───────────────────────────────────────────────────────────────

export function BlockSlotModal({
  slot,
  courtId,
  selectedDate,
  onClose,
  onSuccess,
}: BlockSlotModalProps) {
  const [reason, setReason] = useState('')
  const [apiError, setApiError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const isOpen = slot !== null
  const mode = slot?.status === 'BLOCKED' ? 'unblock' : 'block'

  const timeLabel = slot ? formatTimeBA(slot.start_dt) : ''
  const blockReason = slot?.block_reason ?? null

  // ─── Mutación: bloquear ──────────────────────────────────────────────────────

  const blockMutation = useMutation({
    mutationFn: () => {
      if (!slot || courtId === null) throw new Error('Faltan datos para bloquear el turno.')
      return createSlotBlock({
        court: courtId,
        start_dt: slot.start_dt,
        end_dt: slot.end_dt,
        reason: reason.trim() || undefined,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dailyGridKeys.grid(selectedDate),
      })
      setReason('')
      setApiError(null)
      onSuccess()
    },
    onError: (err) => {
      setApiError(extractApiErrorMessage(err))
    },
  })

  // ─── Mutación: desbloquear ───────────────────────────────────────────────────

  const unblockMutation = useMutation({
    mutationFn: () => {
      if (!slot?.block_id) throw new Error('No se encontró el bloqueo a eliminar.')
      return deleteSlotBlock(slot.block_id)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dailyGridKeys.grid(selectedDate),
      })
      setApiError(null)
      onSuccess()
    },
    onError: (err) => {
      setApiError(extractApiErrorMessage(err))
    },
  })

  // ─── Handlers ────────────────────────────────────────────────────────────────

  function handleClose() {
    setReason('')
    setApiError(null)
    onClose()
  }

  function handleConfirm() {
    setApiError(null)
    if (mode === 'block') {
      blockMutation.mutate()
    } else {
      unblockMutation.mutate()
    }
  }

  const isPending = blockMutation.isPending || unblockMutation.isPending

  // ─── Render ───────────────────────────────────────────────────────────────────

  if (!isOpen) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={mode === 'block' ? 'Bloquear turno' : 'Desbloquear turno'}
      size="sm"
    >
      <div className="space-y-4">
        {/* Icono + info del turno */}
        <div className="flex items-start gap-3 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-4 py-3">
          <span className="mt-0.5 shrink-0 text-gray-400 dark:text-gray-500">
            {mode === 'block' ? (
              <Lock size={16} aria-hidden="true" />
            ) : (
              <Unlock size={16} aria-hidden="true" />
            )}
          </span>
          <div className="text-sm text-gray-700 dark:text-gray-300 space-y-0.5">
            <p className="font-medium">
              Turno de las <strong>{timeLabel}</strong>
            </p>
            {mode === 'unblock' && blockReason && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Motivo del bloqueo: <span className="italic">{blockReason}</span>
              </p>
            )}
          </div>
        </div>

        {/* Campo de motivo (solo al bloquear) */}
        {mode === 'block' && (
          <div className="space-y-1.5">
            <label
              htmlFor="block-reason"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200"
            >
              Motivo{' '}
              <span className="text-gray-400 font-normal">(opcional)</span>
            </label>
            <input
              id="block-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ej: Torneo, Mantenimiento"
              maxLength={200}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            />
          </div>
        )}

        {/* Descripción de la acción */}
        {mode === 'unblock' && (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            ¿Desbloquear este turno? Quedará disponible para reservas.
          </p>
        )}

        {/* Error de API */}
        {apiError && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 px-3 py-2.5"
          >
            <AlertTriangle size={15} className="text-red-500 shrink-0 mt-0.5" aria-hidden="true" />
            <p className="text-sm text-red-700 dark:text-red-400">{apiError}</p>
          </div>
        )}

        {/* Acciones */}
        <div className="flex flex-col-reverse sm:flex-row gap-3 pt-1">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isPending}
            fullWidth
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant={mode === 'block' ? 'danger' : 'primary'}
            onClick={handleConfirm}
            isLoading={isPending}
            fullWidth
          >
            {mode === 'block' ? 'Bloquear' : 'Desbloquear'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
