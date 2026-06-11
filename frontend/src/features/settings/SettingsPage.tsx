/**
 * features/settings/SettingsPage.tsx
 * ------------------------------------
 * Pantalla de configuracion del complejo. Ruta: /admin/settings (tenant_admin).
 *
 * Funcionalidad:
 *  - Carga GET /api/settings/ y pre-rellena el formulario.
 *  - PATCH /api/settings/ con los campos modificados al guardar.
 *  - Toast de exito al guardar; mensaje de error si falla.
 *  - Solo visible para tenant_admin; muestra mensaje de permiso insuficiente al resto.
 *
 * Estados: loading / error / formulario con saving state.
 */

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Settings, CheckCircle2, AlertCircle, Lock } from 'lucide-react'
import { Spinner } from '@/components/Spinner'
import { ErrorState } from '@/components/ErrorState'
import { Button } from '@/components/Button'
import { getComplexSettings, updateComplexSettings } from '@/services/settings'
import { extractApiErrorMessage } from '@/lib/apiError'
import { useAuth } from '@/features/auth/useAuth'
import type { UpdateComplexSettingsRequest } from '@/types/settings'

// ─── Query key ────────────────────────────────────────────────────────────────

export const settingsKeys = {
  all: ['settings'] as const,
}

// ─── Schema de validacion ─────────────────────────────────────────────────────

const settingsSchema = z.object({
  complex_name: z
    .string()
    .min(1, 'El nombre del complejo es obligatorio.')
    .max(200, 'El nombre es demasiado largo.'),
  cbu_number: z.string().max(100, 'Demasiado largo.').optional().or(z.literal('')),
  cbu_alias: z.string().max(100, 'Demasiado largo.').optional().or(z.literal('')),
  account_holder: z.string().max(200, 'Demasiado largo.').optional().or(z.literal('')),
  payment_instructions: z.string().max(1000, 'Demasiado largo.').optional().or(z.literal('')),
  phone: z.string().max(50, 'Demasiado largo.').optional().or(z.literal('')),
  whatsapp: z.string().max(50, 'Demasiado largo.').optional().or(z.literal('')),
  instagram: z.string().max(100, 'Demasiado largo.').optional().or(z.literal('')),
})

type SettingsFormValues = z.infer<typeof settingsSchema>

// ─── Componente de campo de formulario ───────────────────────────────────────

interface FieldProps {
  id: string
  label: string
  error?: string
  required?: boolean
  children: React.ReactNode
}

function Field({ id, label, error, required, children }: FieldProps) {
  return (
    <div className="space-y-1">
      <label
        htmlFor={id}
        className="block text-sm font-medium text-gray-700 dark:text-gray-200"
      >
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-red-500">
            *
          </span>
        )}
      </label>
      {children}
      {error && (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}

function inputClass(hasError: boolean): string {
  return [
    'w-full rounded-lg border px-3 py-2.5 text-sm outline-none',
    'focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
    'transition-colors placeholder:text-gray-400',
    hasError
      ? 'border-red-400 bg-red-50 dark:bg-red-900/20'
      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-100',
  ].join(' ')
}

// ─── Pagina principal ─────────────────────────────────────────────────────────

export function SettingsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  // ── Guard de permisos ────────────────────────────────────────────────────────
  if (user?.role !== 'tenant_admin') {
    return (
      <div className="max-w-lg mx-auto px-4 py-12 flex flex-col items-center gap-4 text-center">
        <Lock size={48} className="text-gray-300 dark:text-gray-600" aria-hidden="true" />
        <h1 className="text-lg font-semibold text-gray-700 dark:text-gray-200">
          Permisos insuficientes
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No tenes permisos para configurar el complejo. Esta seccion es solo para administradores.
        </p>
      </div>
    )
  }

  return <SettingsForm onSaveSuccess={() => setSaveSuccess(true)} queryClient={queryClient} apiError={apiError} setApiError={setApiError} saveSuccess={saveSuccess} setSaveSuccess={setSaveSuccess} />
}

// Separamos el formulario en un componente interno para que el guard de rol no rompa
// las reglas de hooks (hooks no pueden estar despues de un return condicional).

interface SettingsFormProps {
  onSaveSuccess: () => void
  queryClient: ReturnType<typeof useQueryClient>
  apiError: string | null
  setApiError: (e: string | null) => void
  saveSuccess: boolean
  setSaveSuccess: (v: boolean) => void
}

function SettingsForm({ queryClient, apiError, setApiError, saveSuccess, setSaveSuccess }: SettingsFormProps) {
  const {
    data: settings,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: settingsKeys.all,
    queryFn: getComplexSettings,
  })

  const updateMutation = useMutation({
    mutationFn: (payload: UpdateComplexSettingsRequest) => updateComplexSettings(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(settingsKeys.all, updated)
      void queryClient.invalidateQueries({ queryKey: settingsKeys.all })
      setSaveSuccess(true)
      setApiError(null)
      // Ocultar el toast de exito despues de 4 segundos
      setTimeout(() => setSaveSuccess(false), 4000)
    },
    onError: (err) => {
      setApiError(extractApiErrorMessage(err))
      setSaveSuccess(false)
    },
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      complex_name: '',
      cbu_number: '',
      cbu_alias: '',
      account_holder: '',
      payment_instructions: '',
      phone: '',
      whatsapp: '',
      instagram: '',
    },
  })

  // Pre-rellenar el formulario cuando lleguen los datos del servidor
  useEffect(() => {
    if (settings) {
      reset({
        complex_name: settings.complex_name ?? '',
        cbu_number: settings.cbu_number ?? '',
        cbu_alias: settings.cbu_alias ?? '',
        account_holder: settings.account_holder ?? '',
        payment_instructions: settings.payment_instructions ?? '',
        phone: settings.phone ?? '',
        whatsapp: settings.whatsapp ?? '',
        instagram: settings.instagram ?? '',
      })
    }
  }, [settings, reset])

  async function onSubmit(values: SettingsFormValues) {
    setApiError(null)
    setSaveSuccess(false)

    // Solo enviar campos que tienen valor (PATCH parcial)
    const payload: UpdateComplexSettingsRequest = {}
    if (values.complex_name !== undefined) payload.complex_name = values.complex_name
    if (values.cbu_number !== undefined) payload.cbu_number = values.cbu_number ?? ''
    if (values.cbu_alias !== undefined) payload.cbu_alias = values.cbu_alias ?? ''
    if (values.account_holder !== undefined) payload.account_holder = values.account_holder ?? ''
    if (values.payment_instructions !== undefined) payload.payment_instructions = values.payment_instructions ?? ''
    if (values.phone !== undefined) payload.phone = values.phone ?? ''
    if (values.whatsapp !== undefined) payload.whatsapp = values.whatsapp ?? ''
    if (values.instagram !== undefined) payload.instagram = values.instagram ?? ''

    await updateMutation.mutateAsync(payload)
  }

  // ── Estados de carga / error ─────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <Spinner size="lg" label="Cargando configuracion..." />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <ErrorState
          message={extractApiErrorMessage(error)}
          onRetry={() => void refetch()}
          retryLabel="Reintentar"
        />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900 rounded-xl flex items-center justify-center shrink-0">
          <Settings size={20} className="text-brand-600 dark:text-brand-400" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Configuracion del complejo
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Esta informacion se muestra al jugador al hacer una reserva.
          </p>
        </div>
      </div>

      {/* Toast de exito */}
      {saveSuccess && (
        <div
          role="status"
          className="flex items-center gap-2 px-4 py-3 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 text-sm font-medium"
        >
          <CheckCircle2 size={16} aria-hidden="true" />
          Cambios guardados correctamente.
        </div>
      )}

      {/* Error de API */}
      {apiError && (
        <div
          role="alert"
          className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm"
        >
          <AlertCircle size={16} aria-hidden="true" />
          {apiError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {/* ── Datos del complejo ─────────────────────────────────────────── */}
        <section className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">
            Datos del complejo
          </h2>
          <Field
            id="complex_name"
            label="Nombre del complejo"
            error={errors.complex_name?.message}
            required
          >
            <input
              id="complex_name"
              type="text"
              placeholder="Ej: Complejo Los Pinos"
              {...register('complex_name')}
              className={inputClass(!!errors.complex_name)}
            />
          </Field>
        </section>

        {/* ── Datos de pago ──────────────────────────────────────────────── */}
        <section className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">
            Instrucciones de pago
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Esta informacion se muestra al jugador despues de crear una reserva, para que sepa como enviar la seña.
          </p>
          <Field id="cbu_number" label="CBU" error={errors.cbu_number?.message}>
            <input
              id="cbu_number"
              type="text"
              placeholder="Ej: 0000003100012345678901"
              {...register('cbu_number')}
              className={inputClass(!!errors.cbu_number)}
            />
          </Field>
          <Field id="cbu_alias" label="Alias" error={errors.cbu_alias?.message}>
            <input
              id="cbu_alias"
              type="text"
              placeholder="Ej: mi.alias.mercadopago"
              {...register('cbu_alias')}
              className={inputClass(!!errors.cbu_alias)}
            />
          </Field>
          <Field
            id="account_holder"
            label="Titular de la cuenta"
            error={errors.account_holder?.message}
          >
            <input
              id="account_holder"
              type="text"
              placeholder="Ej: Juan Perez"
              {...register('account_holder')}
              className={inputClass(!!errors.account_holder)}
            />
          </Field>
          <Field
            id="payment_instructions"
            label="Instrucciones de pago"
            error={errors.payment_instructions?.message}
          >
            <textarea
              id="payment_instructions"
              rows={3}
              placeholder="Ej: Transferí al CBU indicado y enviá el comprobante por WhatsApp."
              {...register('payment_instructions')}
              className={[
                inputClass(!!errors.payment_instructions),
                'resize-none',
              ].join(' ')}
            />
          </Field>
        </section>

        {/* ── Contacto ──────────────────────────────────────────────────── */}
        <section className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">
            Contacto
          </h2>
          <Field id="phone" label="Telefono" error={errors.phone?.message}>
            <input
              id="phone"
              type="tel"
              placeholder="Ej: 1123456789"
              {...register('phone')}
              className={inputClass(!!errors.phone)}
            />
          </Field>
          <Field id="whatsapp" label="WhatsApp" error={errors.whatsapp?.message}>
            <input
              id="whatsapp"
              type="tel"
              placeholder="Ej: 1123456789"
              {...register('whatsapp')}
              className={inputClass(!!errors.whatsapp)}
            />
          </Field>
          <Field
            id="instagram"
            label="Instagram (@usuario)"
            error={errors.instagram?.message}
          >
            <input
              id="instagram"
              type="text"
              placeholder="Ej: @complejolospinos"
              {...register('instagram')}
              className={inputClass(!!errors.instagram)}
            />
          </Field>
        </section>

        {/* ── Boton guardar ─────────────────────────────────────────────── */}
        <div className="flex justify-end pb-4">
          <Button
            type="submit"
            variant="primary"
            isLoading={updateMutation.isPending}
            disabled={!isDirty && !updateMutation.isPending}
          >
            Guardar cambios
          </Button>
        </div>
      </form>
    </div>
  )
}
