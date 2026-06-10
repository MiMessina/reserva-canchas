/**
 * services/slotBlockService.ts
 * ----------------------------
 * Llamadas a la API para bloquear y desbloquear slots de la grilla.
 * Requiere JWT (operator o tenant_admin).
 *
 * POST /api/slot-blocks/        → crear bloqueo
 * DELETE /api/slot-blocks/{id}/ → eliminar bloqueo
 */

import apiClient from '@/lib/axios'

export interface CreateSlotBlockPayload {
  court: number
  start_dt: string  // ISO UTC
  end_dt: string    // ISO UTC
  reason?: string
}

export interface SlotBlock {
  id: number
  court: number
  start_dt: string
  end_dt: string
  reason: string | null
  created_by: number
  is_active: boolean
  created_at: string
}

export const createSlotBlock = (data: CreateSlotBlockPayload): Promise<SlotBlock> =>
  apiClient.post<SlotBlock>('/api/slot-blocks/', data).then((r) => r.data)

export const deleteSlotBlock = (id: number): Promise<void> =>
  apiClient.delete(`/api/slot-blocks/${id}/`).then(() => undefined)
