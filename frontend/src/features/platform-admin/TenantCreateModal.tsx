/**
 * features/platform-admin/TenantCreateModal.tsx
 * -----------------------------------------------
 * Modal para crear un nuevo tenant desde el panel de platform.
 *
 * Campos: nombre, schema_name, dominio, email admin, contraseña admin.
 * Validaciones con Zod: schema_name solo [a-z][a-z0-9_]*, email válido, todos requeridos.
 * Loading state con "Creando esquema..." (la migración puede tardar 10-15s).
 * Mapeo de errores de negocio del backend.
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Building2, FlaskConical, Radio } from 'lucide-react'
import { Modal } from '@/components/Modal'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { useCreateTenant } from './hooks/usePlatformTenants'
import { extractPlatformApiError } from './platformApiError'

// ─── Schema de validación ─────────────────────────────────────────────────────

const createTenantSchema = z.object({
  name: z.string().min(1, 'El nombre del complejo es obligatorio.').max(100),
  schema_name: z
    .string()
    .min(1, 'El schema es obligatorio.')
    .max(63, 'El schema no puede tener más de 63 caracteres.')
    .regex(
      /^[a-z][a-z0-9_]*$/,
      'El schema solo puede contener letras minúsculas, números y guion bajo, y debe empezar con una letra.',
    )
    .refine(
      (val) =>
        !['public', 'information_schema', 'pg_catalog', 'pg_toast'].includes(val),
      'Ese schema_name está reservado por PostgreSQL.',
    ),
  domain: z
    .string()
    .min(1, 'El dominio es obligatorio.')
    .max(253, 'El dominio es demasiado largo.'),
  admin_email: z
    .string()
    .min(1, 'El email del admin es obligatorio.')
    .email('Ingresá un email válido.'),
  admin_password: z
    .string()
    .min(8, 'La contraseña debe tener al menos 8 caracteres.'),
  bot_mode: z.enum(['mock', 'production']).default('production'),
})

type CreateTenantFormValues = z.infer<typeof createTenantSchema>

// ─── Props ────────────────────────────────────────────────────────────────────

interface TenantCreateModalProps {
  isOpen: boolean
  onClose: () => void
}

// ─── Componente ───────────────────────────────────────────────────────────────

export function TenantCreateModal({ isOpen, onClose }: TenantCreateModalProps) {
  const { mutate: createTenant, isPending, isError, error, reset } = useCreateTenant()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset: resetForm,
    formState: { errors },
  } = useForm<CreateTenantFormValues>({
    resolver: zodResolver(createTenantSchema),
    defaultValues: { bot_mode: 'production' },
  })

  const botMode = watch('bot_mode')

  // Limpiar form y estado de mutación al cerrar/abrir.
  useEffect(() => {
    if (!isOpen) {
      resetForm()
      reset()
    }
  }, [isOpen, resetForm, reset])

  const onSubmit = (data: CreateTenantFormValues) => {
    createTenant(data, {
      onSuccess: () => {
        onClose()
      },
    })
  }

  const errorMessage = isError ? extractPlatformApiError(error) : null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Nuevo complejo" size="lg">
      {errorMessage && (
        <div className="mb-5" role="alert">
          <ErrorState message={errorMessage} compact />
        </div>
      )}

      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        aria-label="Formulario de creación de complejo"
      >
        <div className="space-y-4">
          {/* Nombre del complejo */}
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Nombre del complejo
            </label>
            <input
              id="name"
              type="text"
              aria-invalid={errors.name ? 'true' : 'false'}
              placeholder="Complejo Los Pinos"
              className={inputClass(!!errors.name)}
              {...register('name')}
            />
            {errors.name && (
              <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
            )}
          </div>

          {/* Schema name */}
          <div>
            <label
              htmlFor="schema_name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Schema (identificador técnico)
            </label>
            <input
              id="schema_name"
              type="text"
              aria-invalid={errors.schema_name ? 'true' : 'false'}
              placeholder="lospinos"
              className={inputClass(!!errors.schema_name)}
              {...register('schema_name')}
            />
            <p className="mt-1 text-xs text-gray-400">
              Solo letras minúsculas, números y guion bajo. Ej: lospinos, los_pinos2. No se puede modificar después.
            </p>
            {errors.schema_name && (
              <p className="mt-1 text-xs text-red-600">{errors.schema_name.message}</p>
            )}
          </div>

          {/* Dominio */}
          <div>
            <label
              htmlFor="domain"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Dominio
            </label>
            <input
              id="domain"
              type="text"
              aria-invalid={errors.domain ? 'true' : 'false'}
              placeholder="lospinos.localhost"
              className={inputClass(!!errors.domain)}
              {...register('domain')}
            />
            <p className="mt-1 text-xs text-gray-400">
              Ej: lospinos.localhost (local) o lospinos.canchero.com (producción).
            </p>
            {errors.domain && (
              <p className="mt-1 text-xs text-red-600">{errors.domain.message}</p>
            )}
          </div>

          {/* Modo del bot */}
          <div>
            <p className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
              Modo inicial del bot
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  {
                    value: 'production',
                    label: 'Producción',
                    description: 'Muestra mensajes reales del bot',
                    icon: <Radio size={16} aria-hidden="true" />,
                  },
                  {
                    value: 'mock',
                    label: 'Demo',
                    description: 'Muestra conversaciones de prueba',
                    icon: <FlaskConical size={16} aria-hidden="true" />,
                  },
                ] as const
              ).map((opt) => {
                const selected = botMode === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setValue('bot_mode', opt.value)}
                    className={[
                      'flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors',
                      selected
                        ? 'border-gray-800 bg-gray-800 text-white dark:border-gray-300 dark:bg-gray-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200',
                    ].join(' ')}
                    aria-pressed={selected}
                  >
                    <span className="flex items-center gap-1.5 font-medium">
                      {opt.icon}
                      {opt.label}
                    </span>
                    <span className={['text-xs', selected ? 'text-gray-300' : 'text-gray-400'].join(' ')}>
                      {opt.description}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Separador */}
          <div className="border-t border-gray-100 dark:border-gray-700 pt-2">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
              Credenciales del admin del complejo
            </p>
          </div>

          {/* Email del admin */}
          <div>
            <label
              htmlFor="admin_email"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Email del admin
            </label>
            <input
              id="admin_email"
              type="email"
              inputMode="email"
              aria-invalid={errors.admin_email ? 'true' : 'false'}
              placeholder="admin@lospinos.com"
              className={inputClass(!!errors.admin_email)}
              {...register('admin_email')}
            />
            {errors.admin_email && (
              <p className="mt-1 text-xs text-red-600">{errors.admin_email.message}</p>
            )}
          </div>

          {/* Contraseña del admin */}
          <div>
            <label
              htmlFor="admin_password"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Contraseña del admin
            </label>
            <input
              id="admin_password"
              type="password"
              autoComplete="new-password"
              aria-invalid={errors.admin_password ? 'true' : 'false'}
              placeholder="••••••••"
              className={inputClass(!!errors.admin_password)}
              {...register('admin_password')}
            />
            {errors.admin_password && (
              <p className="mt-1 text-xs text-red-600">
                {errors.admin_password.message}
              </p>
            )}
          </div>
        </div>

        {/* Acciones */}
        <div className="mt-6 flex flex-col-reverse sm:flex-row gap-3 sm:justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            isLoading={isPending}
            leftIcon={<Building2 size={16} />}
            className="bg-gray-800 hover:bg-gray-900 text-white focus:ring-gray-700 disabled:bg-gray-300"
          >
            {isPending ? 'Creando esquema...' : 'Crear complejo'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ─── Helper de clases de input ────────────────────────────────────────────────

function inputClass(hasError: boolean): string {
  return [
    'w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm',
    'focus:outline-none focus:ring-2 focus:ring-gray-500',
    'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400',
    hasError ? 'border-red-400 focus:ring-red-400' : 'border-gray-300',
  ].join(' ')
}
