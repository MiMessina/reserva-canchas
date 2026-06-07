/**
 * components/EmptyState.tsx
 * -------------------------
 * Estado vacío reutilizable. Toda pantalla/listado lo usa cuando no hay datos.
 * Props: title, description (opcional), icon (Lucide), action (opcional).
 */

import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  title?: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

export function EmptyState({
  title = 'No hay datos',
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      aria-label={title}
      className="flex flex-col items-center justify-center py-16 px-4 text-center"
    >
      <span className="text-gray-300 mb-4">
        {icon ?? <Inbox size={48} strokeWidth={1.5} />}
      </span>
      <h3 className="text-base font-semibold text-gray-700">{title}</h3>
      {description && (
        <p className="mt-1 text-sm text-gray-500 max-w-xs">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
