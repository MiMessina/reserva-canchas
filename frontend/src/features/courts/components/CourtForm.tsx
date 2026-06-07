/**
 * features/courts/components/CourtForm.tsx
 * ------------------------------------------
 * Formulario de creacion/edicion de cancha.
 * React Hook Form + Zod. Mobile-first.
 * Usado en modal (nueva cancha) y en pagina de edicion.
 *
 * Props:
 *   - court: Court | null — si se pasa, modo edicion; si no, modo creacion.
 *   - onSuccess: () => void — callback al guardar correctamente.
 *   - onCancel: () => void — callback para cerrar sin guardar.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Save, X } from 'lucide-react'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { useCreateCourt, useUpdateCourt } from '../hooks/useCourts'
import { COURT_TYPE_LABELS } from '../types'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { Court, CourtType } from '../types'

// ─── Schema Zod ──────────────────────────────────────────────────────────────

const courtSchema = z.object({
  name: z
    .string()
    .min(1, 'El nombre es obligatorio.')
    .max(100, 'Maximo 100 caracteres.'),
  court_type: z.enum(['futbol_5', 'futbol_7', 'padel'], {
    required_error: 'Selecciona el tipo de cancha.',
  }),
  surface: z.string().max(50, 'Maximo 50 caracteres.').optional(),
  base_price: z
    .string()
    .min(1, 'El precio base es obligatorio.')
    .regex(/^\d+(\.\d{1,2})?$/, 'Ingresa un precio valido (ej: 15000 o 15000.50).'),
  slot_duration_minutes: z
    .number({
      required_error: 'La duracion del turno es obligatoria.',
      invalid_type_error: 'Ingresa un numero valido.',
    })
    .int('Debe ser un numero entero.')
    .min(30, 'Minimo 30 minutos.')
    .max(240, 'Maximo 240 minutos.'),
})

type CourtFormValues = z.infer<typeof courtSchema>

// ─── Props ────────────────────────────────────────────────────────────────────

interface CourtFormProps {
  court?: Court | null
  onSuccess: () => void
  onCancel: () => void
}

// ─── Componente ───────────────────────────────────────────────────────────────

export function CourtForm({ court, onSuccess, onCancel }: CourtFormProps) {
  const isEditing = court != null

  const createMutation = useCreateCourt()
  const updateMutation = useUpdateCourt()

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CourtFormValues>({
    resolver: zodResolver(courtSchema),
    defaultValues: {
      name: court?.name ?? '',
      court_type: (court?.court_type ?? 'futbol_5') as CourtType,
      surface: court?.surface ?? '',
      base_price: court?.base_price ?? '',
      slot_duration_minutes: court?.slot_duration_minutes ?? 60,
    },
  })

  const onSubmit = (values: CourtFormValues) => {
    const payload = {
      name: values.name,
      court_type: values.court_type,
      surface: values.surface || '',
      base_price: values.base_price,
      slot_duration_minutes: values.slot_duration_minutes,
    }

    if (isEditing) {
      updateMutation.mutate(
        { id: court.id, payload },
        { onSuccess },
      )
    } else {
      createMutation.mutate(payload, { onSuccess })
    }
  }

  const inputClass = (hasError: boolean) =>
    [
      'w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm bg-white',
      'focus:outline-none focus:ring-2 focus:ring-brand-500',
      hasError ? 'border-red-400 focus:ring-red-400' : 'border-gray-300',
    ].join(' ')

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      aria-label={isEditing ? 'Editar cancha' : 'Nueva cancha'}
      className="space-y-4"
    >
      {/* Error de API */}
      {mutationError && (
        <div role="alert">
          <ErrorState
            message={extractApiErrorMessage(mutationError)}
            compact
          />
        </div>
      )}

      {/* Nombre */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          Nombre <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <input
          id="name"
          type="text"
          autoComplete="off"
          placeholder="Ej: Cancha 1"
          aria-invalid={errors.name ? 'true' : 'false'}
          aria-describedby={errors.name ? 'name-error' : undefined}
          className={inputClass(!!errors.name)}
          {...register('name')}
        />
        {errors.name && (
          <p id="name-error" className="mt-1 text-xs text-red-600">
            {errors.name.message}
          </p>
        )}
      </div>

      {/* Tipo de cancha */}
      <div>
        <label htmlFor="court_type" className="block text-sm font-medium text-gray-700 mb-1">
          Tipo <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <select
          id="court_type"
          aria-invalid={errors.court_type ? 'true' : 'false'}
          className={inputClass(!!errors.court_type)}
          {...register('court_type')}
        >
          {(Object.entries(COURT_TYPE_LABELS) as [CourtType, string][]).map(
            ([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ),
          )}
        </select>
        {errors.court_type && (
          <p className="mt-1 text-xs text-red-600">{errors.court_type.message}</p>
        )}
      </div>

      {/* Superficie */}
      <div>
        <label htmlFor="surface" className="block text-sm font-medium text-gray-700 mb-1">
          Superficie <span className="text-xs text-gray-400">(opcional)</span>
        </label>
        <input
          id="surface"
          type="text"
          placeholder="Ej: Cesped sintetico"
          className={inputClass(!!errors.surface)}
          {...register('surface')}
        />
        {errors.surface && (
          <p className="mt-1 text-xs text-red-600">{errors.surface.message}</p>
        )}
      </div>

      {/* Precio base */}
      <div>
        <label htmlFor="base_price" className="block text-sm font-medium text-gray-700 mb-1">
          Precio base (ARS) <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <input
          id="base_price"
          type="text"
          inputMode="decimal"
          placeholder="Ej: 15000"
          aria-invalid={errors.base_price ? 'true' : 'false'}
          aria-describedby={errors.base_price ? 'price-error' : undefined}
          className={inputClass(!!errors.base_price)}
          {...register('base_price')}
        />
        {errors.base_price && (
          <p id="price-error" className="mt-1 text-xs text-red-600">
            {errors.base_price.message}
          </p>
        )}
      </div>

      {/* Duracion del turno */}
      <div>
        <label htmlFor="slot_duration" className="block text-sm font-medium text-gray-700 mb-1">
          Duracion del turno (min) <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <select
          id="slot_duration"
          aria-invalid={errors.slot_duration_minutes ? 'true' : 'false'}
          className={inputClass(!!errors.slot_duration_minutes)}
          {...register('slot_duration_minutes', { valueAsNumber: true })}
        >
          <option value={30}>30 minutos</option>
          <option value={60}>60 minutos</option>
          <option value={90}>90 minutos</option>
          <option value={120}>120 minutos</option>
        </select>
        {errors.slot_duration_minutes && (
          <p className="mt-1 text-xs text-red-600">
            {errors.slot_duration_minutes.message}
          </p>
        )}
      </div>

      {/* Acciones */}
      <div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
        <Button
          type="button"
          variant="secondary"
          fullWidth
          leftIcon={<X size={16} />}
          onClick={onCancel}
          disabled={isPending}
        >
          Cancelar
        </Button>
        <Button
          type="submit"
          fullWidth
          isLoading={isPending}
          leftIcon={<Save size={16} />}
        >
          {isEditing ? 'Guardar cambios' : 'Crear cancha'}
        </Button>
      </div>
    </form>
  )
}
