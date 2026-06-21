import { useQuery } from '@tanstack/react-query'
import { getComplexSettings } from '@/services/settings'

/**
 * Retorna el nombre público del complejo activo.
 * Consume GET /api/settings/ (público, sin JWT).
 * Fallback: 'CANCHERO!' para tenants sin complex_name configurado.
 */
export function useTenantInfo() {
  const { data, isLoading } = useQuery({
    queryKey: ['tenant-info'],
    queryFn: getComplexSettings,
    staleTime: 5 * 60 * 1000,
  })

  return {
    complexName: data?.complex_name || 'CANCHERO!',
    isLoading,
  }
}
