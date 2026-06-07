/**
 * components/Spinner.tsx
 * ----------------------
 * Indicador de carga accesible (role="status", aria-label).
 * Tamaños: sm / md / lg. Colores: brand / gray / white.
 */

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  color?: 'brand' | 'gray' | 'white'
  label?: string
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-10 h-10 border-[3px]',
}

const colorClasses = {
  brand: 'border-brand-200 border-t-brand-600',
  gray: 'border-gray-200 border-t-gray-600',
  white: 'border-white/30 border-t-white',
}

export function Spinner({
  size = 'md',
  color = 'brand',
  label = 'Cargando...',
}: SpinnerProps) {
  return (
    <span role="status" aria-label={label} className="inline-block">
      <span
        className={[
          'block rounded-full animate-spin',
          sizeClasses[size],
          colorClasses[color],
        ].join(' ')}
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}
