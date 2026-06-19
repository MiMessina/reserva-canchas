/**
 * features/platform-admin/hooks/usePlatformTenants.ts
 * -----------------------------------------------------
 * Hooks de TanStack Query para el CRUD de tenants del panel de platform.
 *
 * Query keys:
 *   ["platform-tenants"]         → lista de tenants
 *   ["platform-tenants", id]     → detalle de un tenant
 *
 * Reglas:
 * - Invalidar ["platform-tenants"] tras toda mutación.
 * - Usar platformApiClient (nunca el apiClient de tenant).
 * - No calcular ni decidir nada: solo transporte HTTP + cache.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query'
import platformApiClient from '@/lib/platformApiClient'
import type { PaginatedResponse } from '@/types/api'
import type {
  Tenant,
  TenantCreatePayload,
  TenantUpdatePayload,
} from '../types'

// ─── Query keys ──────────────────────────────────────────────────────────────

export const platformTenantKeys = {
  all: ['platform-tenants'] as const,
  list: () => ['platform-tenants', 'list'] as const,
  detail: (id: number) => ['platform-tenants', id] as const,
}

// ─── Funciones de servicio (inline — solo las usa este hook) ─────────────────

async function fetchTenants(): Promise<PaginatedResponse<Tenant>> {
  const { data } = await platformApiClient.get<PaginatedResponse<Tenant>>('/tenants/')
  return data
}

async function fetchTenant(id: number): Promise<Tenant> {
  const { data } = await platformApiClient.get<Tenant>(`/tenants/${id}/`)
  return data
}

async function createTenantApi(payload: TenantCreatePayload): Promise<Tenant> {
  const { data } = await platformApiClient.post<Tenant>('/tenants/', payload)
  return data
}

async function toggleTenantApi(id: number): Promise<Tenant> {
  const { data } = await platformApiClient.post<Tenant>(`/tenants/${id}/toggle/`)
  return data
}

async function updateTenantApi(id: number, payload: TenantUpdatePayload): Promise<Tenant> {
  const { data } = await platformApiClient.patch<Tenant>(`/tenants/${id}/`, payload)
  return data
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function usePlatformTenants(): UseQueryResult<PaginatedResponse<Tenant>> {
  return useQuery({
    queryKey: platformTenantKeys.list(),
    queryFn: fetchTenants,
  })
}

export function usePlatformTenant(id: number): UseQueryResult<Tenant> {
  return useQuery({
    queryKey: platformTenantKeys.detail(id),
    queryFn: () => fetchTenant(id),
    enabled: id > 0,
  })
}

export function useCreateTenant(): UseMutationResult<
  Tenant,
  Error,
  TenantCreatePayload
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createTenantApi,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformTenantKeys.all })
    },
  })
}

export function useToggleTenant(): UseMutationResult<Tenant, Error, number> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: toggleTenantApi,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformTenantKeys.all })
    },
  })
}

export function useUpdateTenant(): UseMutationResult<
  Tenant,
  Error,
  { id: number; payload: TenantUpdatePayload }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }) => updateTenantApi(id, payload),
    onSuccess: (updatedTenant) => {
      queryClient.setQueryData(
        platformTenantKeys.detail(updatedTenant.id),
        updatedTenant,
      )
      void queryClient.invalidateQueries({ queryKey: platformTenantKeys.all })
    },
  })
}
