/**
 * features/users/hooks/useOperators.ts
 * --------------------------------------
 * Hooks de React Query para la gestion de operadores.
 *
 * Query keys:
 *   ["operators"]  → lista de operadores del tenant
 *
 * Invalidacion tras cada mutacion:
 *   - createOperator → invalida ["operators"]
 *   - deleteOperator → invalida ["operators"]
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query'
import {
  getOperators,
  createOperator,
  deleteOperator,
} from '../services/users.service'
import type { CreateOperatorPayload, Operator } from '../types'
import type { PaginatedResponse } from '@/types/api'

// ─── Query keys ───────────────────────────────────────────────────────────────

export const operatorKeys = {
  all: ['operators'] as const,
}

// ─── Queries ──────────────────────────────────────────────────────────────────

export function useOperators(): UseQueryResult<PaginatedResponse<Operator>> {
  return useQuery({
    queryKey: operatorKeys.all,
    queryFn: getOperators,
  })
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export function useCreateOperator(): UseMutationResult<
  Operator,
  Error,
  CreateOperatorPayload
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createOperator,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: operatorKeys.all })
    },
  })
}

export function useDeleteOperator(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteOperator,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: operatorKeys.all })
    },
  })
}
