/**
 * features/courts/components/ScheduleBlockForm.tsx
 * --------------------------------------------------
 * Formulario para crear/editar un bloque horario de una cancha.
 * React Hook Form + Zod. Mobile-first.
 *
 * IMPORTANTE: open_time y close_time son horas de pared del complejo.
 * NO se aplica conversion de timezone. Se muestran y envian tal cual (HH:MM).
 *
 * Errores de negocio manejados:
 *   - INVALID_SCHEDULE: open_time >= close_time
 *   - SCHEDULE_OVERLAP: bloque superpuesto mismo dia/cancha
 *
 * Props:
 *   - courtId: number — cancha a la que pertenece el bloque
 *   - block: ScheduleBlock | null — si se pasa, modo edicion
 *   - onSuccess: () => void
 *   - onCancel: () => void
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Save, X } from 'lucide-react'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { useCreateScheduleBlock, useUpdateScheduleBlock } from '../hooks/useCourts'
import { WEEKDAY_OPTIONS } from '../types'
import { extractApiErrorMessage } from '@/lib/apiError'
import type { ScheduleBlock, Weekday } from '../types'

// ─── Schema Zod ──────────────────────────────────────────────────────────────

const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/

const scheduleBlockSchema = z
  .object({
    weekday: z.coerce.number().min(0).max(6) as z.ZodType<Weekday>,
    open_time: z
      .string()
      .regex(timeRegex, 'Formato invalido. Usa HH:MM (ej: 08:00).'),
    close_time: z
      .string()
      .regex(timeRegex, 'Formato invalido. Usa HH:MM (ej: 22:00).'),
  })
  .refine((data) => data.open_time < data.close_time, {
    message: 'El horario de apertura debe ser anterior al de cierre.',
    path: ['close_time'],
  })

type ScheduleBlockFormValues = z.infer<typeof scheduleBlockSchema>

// ─── Helper: "HH:MM:SS" → "HH:MM" ───────────────────────────────────────────

function toHHMM(timeStr: string): string {
  // El backend puede devolver "HH:MM:SS"; el input solo necesita "HH:MM".
  return timeStr.slice(0, 5)
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface ScheduleBlockFormProps {
  courtId: number
  block?: ScheduleBlock | null
  onSuccess: () => void
  onCancel: () => void
}

// ─── Componente ───────────────────────────────────────────────────────────────

export function ScheduleBlockForm({
  courtId,
  block,
  onSuccess,
  onCancel,
}: ScheduleBlockFormProps) {
  const isEditing = block != null

  const createMutation = useCreateScheduleBlock()
  const updateMutation = useUpdateScheduleBlock()

  const isPending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error || updateMutation.error

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ScheduleBlockFormValues>({
    resolver: zodResolver(scheduleBlockSchema),
    defaultValues: {
      weekday: (block?.weekday ?? 0) as Weekday,
      open_time: block ? toHHMM(block.open_time) : '08:00',
      close_time: block ? toHHMM(block.close_time) : '22:00',
    },
  })

  const onSubmit = (values: ScheduleBlockFormValues) => {
    if (isEditing) {
      updateMutation.mutate(
        {
          id: block.id,
          courtId,
          payload: {
            weekday: values.weekday,
            open_time: values.open_time,
            close_time: values.close_time,
          },
        },
        { onSuccess },
      )
    } else {
      createMutation.mutate(
        {
          court: courtId,
          weekday: values.weekday,
          open_time: values.open_time,
          close_time: values.close_time,
        },
        { onSuccess },
      )
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
      aria-label={isEditing ? 'Editar bloque horario' : 'Nuevo bloque horario'}
      className="space-y-4"
    >
      {/* Error de API (incluye INVALID_SCHEDULE y SCHEDULE_OVERLAP) */}
      {mutationError && (
        <div role="alert">
          <ErrorState
            message={extractApiErrorMessage(mutationError)}
            compact
          />
        </div>
      )}

      {/* Dia de la semana */}
      <div>
        <label htmlFor="weekday" className="block text-sm font-medium text-gray-700 mb-1">
          Dia <span aria-hidden="true" className="text-red-500">*</span>
        </label>
        <select
          id="weekday"
          aria-invalid={errors.weekday ? 'true' : 'false'}
          className={inputClass(!!errors.weekday)}
          {...register('weekday')}
        >
          {WEEKDAY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.weekday && (
          <p className="mt-1 text-xs text-red-600">{errors.weekday.message}</p>
        )}
      </div>

      {/* Horarios: apertura y cierre en la misma fila en pantallas medianas */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="open_time" className="block text-sm font-medium text-gray-700 mb-1">
            Apertura <span aria-hidden="true" className="text-red-500">*</span>
          </label>
          <input
            id="open_time"
            type="time"
            aria-invalid={errors.open_time ? 'true' : 'false'}
            aria-describedby={errors.open_time ? 'open-time-error' : undefined}
            className={inputClass(!!errors.open_time)}
            {...register('open_time')}
          />
          {errors.open_time && (
            <p id="open-time-error" className="mt-1 text-xs text-red-600">
              {errors.open_time.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="close_time" className="block text-sm font-medium text-gray-700 mb-1">
            Cierre <span aria-hidden="true" className="text-red-500">*</span>
          </label>
          <input
            id="close_time"
            type="time"
            aria-invalid={errors.close_time ? 'true' : 'false'}
            aria-describedby={errors.close_time ? 'close-time-error' : undefined}
            className={inputClass(!!errors.close_time)}
            {...register('close_time')}
          />
          {errors.close_time && (
            <p id="close-time-error" className="mt-1 text-xs text-red-600">
              {errors.close_time.message}
            </p>
          )}
        </div>
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
          {isEditing ? 'Guardar cambios' : 'Agregar bloque'}
        </Button>
      </div>
    </form>
  )
}
