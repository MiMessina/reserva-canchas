/**
 * features/courts/services/courts.service.ts
 * --------------------------------------------
 * Llamadas a la API de Canchas y Bloques Horarios.
 * Usa el cliente axios central (lib/axios.ts).
 * No contiene logica de negocio: solo transporte HTTP.
 *
 * Endpoints:
 *   GET    /api/courts/                   → lista paginada
 *   POST   /api/courts/                   → crear cancha (tenant_admin)
 *   GET    /api/courts/{id}/              → detalle
 *   PATCH  /api/courts/{id}/              → editar (tenant_admin)
 *   DELETE /api/courts/{id}/              → baja logica (tenant_admin)
 *
 *   GET    /api/schedule-blocks/          → lista paginada (filtros: court, weekday)
 *   POST   /api/schedule-blocks/          → crear bloque (tenant_admin)
 *   GET    /api/schedule-blocks/{id}/     → detalle
 *   PATCH  /api/schedule-blocks/{id}/     → editar (tenant_admin)
 *   DELETE /api/schedule-blocks/{id}/     → baja logica (tenant_admin)
 */

import apiClient from '@/lib/axios'
import type { PaginatedResponse } from '@/types/api'
import type {
  Court,
  CourtsFilters,
  CreateCourtPayload,
  UpdateCourtPayload,
  ScheduleBlock,
  ScheduleBlocksFilters,
  CreateScheduleBlockPayload,
  UpdateScheduleBlockPayload,
} from '../types'

// ─── Courts ──────────────────────────────────────────────────────────────────

export async function getCourts(
  filters?: CourtsFilters,
): Promise<PaginatedResponse<Court>> {
  const { data } = await apiClient.get<PaginatedResponse<Court>>('/courts/', {
    params: filters,
  })
  return data
}

export async function getCourt(id: number): Promise<Court> {
  const { data } = await apiClient.get<Court>(`/courts/${id}/`)
  return data
}

export async function createCourt(payload: CreateCourtPayload): Promise<Court> {
  const { data } = await apiClient.post<Court>('/courts/', payload)
  return data
}

export async function updateCourt(
  id: number,
  payload: UpdateCourtPayload,
): Promise<Court> {
  const { data } = await apiClient.patch<Court>(`/courts/${id}/`, payload)
  return data
}

/**
 * Baja logica: el backend pone is_active=false (soft-delete).
 * Confirmado por API_GUIDELINES.md: DELETE = baja logica, no borrado fisico.
 */
export async function deleteCourt(id: number): Promise<void> {
  await apiClient.delete(`/courts/${id}/`)
}

// ─── ScheduleBlocks ───────────────────────────────────────────────────────────

export async function getScheduleBlocks(
  filters?: ScheduleBlocksFilters,
): Promise<PaginatedResponse<ScheduleBlock>> {
  const { data } = await apiClient.get<PaginatedResponse<ScheduleBlock>>(
    '/schedule-blocks/',
    { params: filters },
  )
  return data
}

export async function getScheduleBlock(id: number): Promise<ScheduleBlock> {
  const { data } = await apiClient.get<ScheduleBlock>(`/schedule-blocks/${id}/`)
  return data
}

export async function createScheduleBlock(
  payload: CreateScheduleBlockPayload,
): Promise<ScheduleBlock> {
  const { data } = await apiClient.post<ScheduleBlock>('/schedule-blocks/', payload)
  return data
}

export async function updateScheduleBlock(
  id: number,
  payload: UpdateScheduleBlockPayload,
): Promise<ScheduleBlock> {
  const { data } = await apiClient.patch<ScheduleBlock>(
    `/schedule-blocks/${id}/`,
    payload,
  )
  return data
}

export async function deleteScheduleBlock(id: number): Promise<void> {
  await apiClient.delete(`/schedule-blocks/${id}/`)
}
