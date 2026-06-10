/**
 * app/Providers.tsx
 * -----------------
 * Wrapper de providers globales:
 *   - QueryClientProvider (TanStack Query)
 *
 * El RouterProvider vive en AppRouter para poder usar useNavigate dentro
 * de los providers sin necesidad de un router externo.
 *
 * Configuración de QueryClient:
 *   - staleTime: 30s (los datos de grilla y caja se consideran frescos 30s).
 *   - retry: 1 (reintenta una vez antes de mostrar error).
 *   - refetchOnWindowFocus: false (evita refetches agresivos en mobile).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { ThemeProvider } from '@/context/ThemeContext'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30 segundos
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})

interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </ThemeProvider>
  )
}
