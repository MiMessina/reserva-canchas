/**
 * features/courts/hooks/useCourts.ts
 * ------------------------------------
 * Hooks de React Query para Canchas y Bloques Horarios.
 *
 * Query keys (consistentes por dominio, siguiendo API_GUIDELINES.md):
 *   ["courts"]              → lista de canchas
 *   ["courts", id]          → detalle de cancha
 *   ["schedule-blocks", courtId] → bloques de una cancha
 *
 * Invalidacion de cache tras cada mutacion (crear/editar/eliminar).
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query'
import {
  getCourts,
  getCourt,
  createCourt,
  updateCourt,
  deleteCourt,
  getScheduleBlocks,
  createScheduleBlock,
  updateScheduleBlock,
  deleteScheduleBlock,
} from '../services/courts.service'
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
import type { PaginatedResponse } from '@/types/api'

// ─── Query keys ──────────────────────────────────────────────────────────────

export const courtKeys = {
  all: ['courts'] as const,
  list: (filters?: CourtsFilters) => ['courts', 'list', filters] as const,
  detail: (id: number) => ['courts', id] as const,
}

export const scheduleBlockKeys = {
  all: ['schedule-blocks'] as const,
  byCourt: (courtId: number) => ['schedule-blocks', 'court', courtId] as const,
  list: (filters?: ScheduleBlocksFilters) =>
    ['schedule-blocks', 'list', filters] as const,
}

// ─── Courts — Queries ─────────────────────────────────────────────────────────

export function useCourts(
  filters?: CourtsFilters,
): UseQueryResult<PaginatedResponse<Court>> {
  return useQuery({
    queryKey: courtKeys.list(filters),
    queryFn: () => getCourts(filters),
  })
}

export function useCourt(id: number): UseQueryResult<Court> {
  return useQuery({
    queryKey: courtKeys.detail(id),
    queryFn: () => getCourt(id),
    enabled: id > 0,
  })
}

// ─── Courts — Mutations ───────────────────────────────────────────────────────

export function useCreateCourt(): UseMutationResult<
  Court,
  Error,
  CreateCourtPayload
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCourt,
    onSuccess: () => {
      // Invalidar lista de canchas para que se refrescara automaticamente.
      void queryClient.invalidateQueries({ queryKey: courtKeys.all })
    },
  })
}

export function useUpdateCourt(): UseMutationResult<
  Court,
  Error,
  { id: number; payload: UpdateCourtPayload }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }) => updateCourt(id, payload),
    onSuccess: (updatedCourt) => {
      // Actualizar el detalle en cache directamente (evita un round-trip).
      queryClient.setQueryData(courtKeys.detail(updatedCourt.id), updatedCourt)
      // Invalidar la lista para que refleje el cambio.
      void queryClient.invalidateQueries({ queryKey: courtKeys.all })
    },
  })
}

export function useDeleteCourt(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCourt,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: courtKeys.all })
    },
  })
}

// ─── ScheduleBlocks — Queries ─────────────────────────────────────────────────

export function useScheduleBlocks(
  courtId: number,
): UseQueryResult<PaginatedResponse<ScheduleBlock>> {
  return useQuery({
    queryKey: scheduleBlockKeys.byCourt(courtId),
    queryFn: () => getScheduleBlocks({ court: courtId }),
    enabled: courtId > 0,
  })
}

// ─── ScheduleBlocks — Mutations ───────────────────────────────────────────────

export function useCreateScheduleBlock(): UseMutationResult<
  ScheduleBlock,
  Error,
  CreateScheduleBlockPayload
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createScheduleBlock,
    onSuccess: (newBlock) => {
      void queryClient.invalidateQueries({
        queryKey: scheduleBlockKeys.byCourt(newBlock.court),
      })
    },
  })
}

export function useUpdateScheduleBlock(): UseMutationResult<
  ScheduleBlock,
  Error,
  { id: number; courtId: number; payload: UpdateScheduleBlockPayload }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }) => updateScheduleBlock(id, payload),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: scheduleBlockKeys.byCourt(variables.courtId),
      })
    },
  })
}

export function useDeleteScheduleBlock(): UseMutationResult<
  void,
  Error,
  { id: number; courtId: number }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id }) => deleteScheduleBlock(id),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: scheduleBlockKeys.byCourt(variables.courtId),
      })
    },
  })
}
