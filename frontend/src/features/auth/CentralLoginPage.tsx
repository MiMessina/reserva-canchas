/**
 * features/auth/CentralLoginPage.tsx
 * ------------------------------------
 * Login centralizado desde app.localhost:5173/login (Sprint 14).
 *
 * Flujo de 2 pasos:
 *   Paso 1 — Email:
 *     - El usuario ingresa su email.
 *     - Se llama a lookupEmailApi(email).
 *     - 0 resultados → error "No encontramos tu email en ningún complejo."
 *     - 1 resultado → avanza automáticamente al Paso 2 con ese tenant.
 *     - N resultados → muestra selector de complejo → al elegir avanza al Paso 2.
 *
 *   Paso 2 — Contraseña:
 *     - Muestra el nombre del complejo seleccionado.
 *     - El usuario ingresa su contraseña.
 *     - Se llama a centralLoginApi(email, password, schema_name).
 *     - En éxito → redirección hard a redirect_url?code=<code> (cambia subdominio).
 *     - En error → mensaje claro en español.
 *     - Botón "← Cambiar complejo" para volver al Paso 1 manteniendo el email.
 *
 * Errores mapeados:
 *   TENANT_INACTIVE   → "Este complejo no está activo. Contactá al administrador."
 *   INVALID_CREDENTIALS → "Email o contraseña incorrectos. Revisá tus datos."
 *   ROLE_NOT_ALLOWED  → "Tu cuenta no tiene permisos para ingresar desde aquí."
 *   Otros             → "No se pudo iniciar sesión. Intentá de nuevo."
 *
 * Estilo: misma estética que LoginPage.tsx (CANCHERO! header, card centrada,
 * dark mode, mobile-first, Tailwind, Lucide React).
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { LogIn, ArrowLeft, Building2, ChevronRight } from 'lucide-react'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { Spinner } from '@/components/Spinner'
import {
  lookupEmailApi,
  centralLoginApi,
  type TenantMatch,
} from '@/services/centralAuth.service'

// ─── Schemas de validación ────────────────────────────────────────────────────

const emailSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es obligatorio.')
    .email('Ingresá un email válido.'),
})

const passwordSchema = z.object({
  password: z
    .string()
    .min(1, 'La contraseña es obligatoria.')
    .min(4, 'La contraseña es demasiado corta.'),
})

type EmailFormValues = z.infer<typeof emailSchema>
type PasswordFormValues = z.infer<typeof passwordSchema>

// ─── Tipos de estado ──────────────────────────────────────────────────────────

type Step = 'email' | 'select-tenant' | 'password'

// ─── Helper: mapear códigos de error del backend ──────────────────────────────

function mapApiError(err: unknown): string {
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'data' in err.response
  ) {
    const data = (err.response as { data: unknown }).data
    if (
      data &&
      typeof data === 'object' &&
      'error' in data &&
      data.error &&
      typeof data.error === 'object' &&
      'code' in data.error
    ) {
      const code = (data.error as { code: string }).code
      switch (code) {
        case 'TENANT_INACTIVE':
          return 'Este complejo no está activo. Contactá al administrador.'
        case 'INVALID_CREDENTIALS':
          return 'Email o contraseña incorrectos. Revisá tus datos.'
        case 'ROLE_NOT_ALLOWED':
          return 'Tu cuenta no tiene permisos para ingresar desde aquí.'
        default:
          return 'No se pudo iniciar sesión. Intentá de nuevo.'
      }
    }
  }
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'status' in err.response
  ) {
    const status = (err.response as { status: number }).status
    if (status >= 500) return 'Error del servidor. Intentá de nuevo en unos momentos.'
  }
  return 'Sin conexión. Verificá tu red e intentá de nuevo.'
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function CentralLoginPage() {
  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [tenants, setTenants] = useState<TenantMatch[]>([])
  const [selectedTenant, setSelectedTenant] = useState<TenantMatch | null>(null)

  const [isLookingUp, setIsLookingUp] = useState(false)
  const [lookupError, setLookupError] = useState<string | null>(null)

  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  // ─── Formulario Paso 1: email ─────────────────────────────────────────────

  const emailForm = useForm<EmailFormValues>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: '' },
  })

  const onEmailSubmit = async (data: EmailFormValues) => {
    setLookupError(null)
    setIsLookingUp(true)
    try {
      const matches = await lookupEmailApi(data.email)
      setEmail(data.email)
      if (matches.length === 0) {
        setLookupError('No encontramos tu email en ningún complejo.')
        return
      }
      setTenants(matches)
      if (matches.length === 1) {
        // Un solo complejo: saltar directamente al paso de contraseña
        setSelectedTenant(matches[0])
        setStep('password')
      } else {
        // Múltiples complejos: mostrar selector
        setStep('select-tenant')
      }
    } catch {
      setLookupError('No se pudo verificar el email. Intentá de nuevo.')
    } finally {
      setIsLookingUp(false)
    }
  }

  // ─── Selección de tenant (cuando hay múltiples) ───────────────────────────

  const onTenantSelect = (tenant: TenantMatch) => {
    setSelectedTenant(tenant)
    setLoginError(null)
    setStep('password')
  }

  // ─── Formulario Paso 2: contraseña ────────────────────────────────────────

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
  })

  const onPasswordSubmit = async (data: PasswordFormValues) => {
    if (!selectedTenant) return
    setLoginError(null)
    setIsLoggingIn(true)
    try {
      const { code, redirect_url } = await centralLoginApi(
        email,
        data.password,
        selectedTenant.schema_name,
      )
      // Redirección hard: cambia el subdominio (de app.localhost a <tenant>.localhost)
      // El tenant destino detectará ?code= y lo intercambiará por JWT (useCodeExchange).
      const separator = redirect_url.includes('?') ? '&' : '?'
      window.location.href = `${redirect_url}${separator}code=${code}`
    } catch (err) {
      setLoginError(mapApiError(err))
    } finally {
      setIsLoggingIn(false)
    }
  }

  const handleBackToEmail = () => {
    setStep('email')
    setSelectedTenant(null)
    setLoginError(null)
    // Restaurar el email en el formulario
    emailForm.setValue('email', email)
  }

  const handleBackToTenantSelect = () => {
    setStep('select-tenant')
    setSelectedTenant(null)
    setLoginError(null)
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
        {/* Logo / Marca */}
        <div className="flex justify-center">
          <div className="w-12 h-12 bg-brand-600 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-xl">C</span>
          </div>
        </div>
        <h1 className="mt-6 text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
          CANCHERO!
        </h1>
        <p className="mt-1 text-center text-sm text-gray-500 dark:text-gray-400">
          Ingresá a tu cuenta
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-sm rounded-2xl sm:px-8">

          {/* ─── PASO 1: Email ─────────────────────────────────────────────── */}
          {step === 'email' && (
            <form
              onSubmit={emailForm.handleSubmit(onEmailSubmit)}
              noValidate
              aria-label="Formulario de inicio de sesión centralizado — paso email"
            >
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">
                Ingresá tu email
              </h2>

              {lookupError && (
                <div className="mb-4" role="alert">
                  <ErrorState message={lookupError} compact />
                </div>
              )}

              <div className="mb-5">
                <label
                  htmlFor="central-email"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                >
                  Email
                </label>
                <input
                  id="central-email"
                  type="email"
                  autoComplete="email"
                  inputMode="email"
                  aria-invalid={emailForm.formState.errors.email ? 'true' : 'false'}
                  aria-describedby={emailForm.formState.errors.email ? 'central-email-error' : undefined}
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm
                    focus:outline-none focus:ring-2 focus:ring-brand-500
                    dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400
                    ${emailForm.formState.errors.email
                      ? 'border-red-400 focus:ring-red-400'
                      : 'border-gray-300'
                    }`}
                  placeholder="tu@email.com"
                  {...emailForm.register('email')}
                />
                {emailForm.formState.errors.email && (
                  <p id="central-email-error" className="mt-1 text-xs text-red-600">
                    {emailForm.formState.errors.email.message}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                isLoading={isLookingUp}
                fullWidth
                rightIcon={<ChevronRight size={16} />}
              >
                Continuar
              </Button>
            </form>
          )}

          {/* ─── PASO 1b: Selector de complejo (N tenants) ────────────────── */}
          {step === 'select-tenant' && (
            <div>
              <button
                type="button"
                onClick={handleBackToEmail}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 mb-4"
              >
                <ArrowLeft size={14} />
                Cambiar email
              </button>

              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
                Elegí tu complejo
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                Tu email tiene cuenta en más de un complejo.
              </p>

              <ul
                className="space-y-2"
                role="listbox"
                aria-label="Complejos disponibles para tu cuenta"
              >
                {tenants.map((tenant) => (
                  <li key={tenant.schema_name}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selectedTenant?.schema_name === tenant.schema_name}
                      onClick={() => onTenantSelect(tenant)}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200
                        dark:border-gray-700 bg-white dark:bg-gray-700/50 hover:bg-brand-50
                        dark:hover:bg-brand-900/20 hover:border-brand-300 dark:hover:border-brand-700
                        text-left transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      <Building2 size={18} className="text-brand-500 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
                          {tenant.tenant_name}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
                          {tenant.domain}
                        </p>
                      </div>
                      <ChevronRight size={16} className="ml-auto text-gray-400 shrink-0" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ─── PASO 2: Contraseña ────────────────────────────────────────── */}
          {step === 'password' && selectedTenant && (
            <form
              onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}
              noValidate
              aria-label="Formulario de inicio de sesión centralizado — paso contraseña"
            >
              {/* Botón volver */}
              <button
                type="button"
                onClick={tenants.length > 1 ? handleBackToTenantSelect : handleBackToEmail}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 mb-4"
              >
                <ArrowLeft size={14} />
                {tenants.length > 1 ? 'Cambiar complejo' : 'Cambiar email'}
              </button>

              {/* Complejo seleccionado */}
              <div className="flex items-center gap-2 mb-5 p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
                <Building2 size={16} className="text-brand-500 shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Complejo</p>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
                    {selectedTenant.tenant_name}
                  </p>
                </div>
              </div>

              {/* Error de login */}
              {loginError && (
                <div className="mb-4" role="alert">
                  <ErrorState message={loginError} compact />
                </div>
              )}

              {/* Campo: Contraseña */}
              <div className="mb-6">
                <label
                  htmlFor="central-password"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                >
                  Contraseña
                </label>
                <input
                  id="central-password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={passwordForm.formState.errors.password ? 'true' : 'false'}
                  aria-describedby={passwordForm.formState.errors.password ? 'central-password-error' : undefined}
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm
                    focus:outline-none focus:ring-2 focus:ring-brand-500
                    dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400
                    ${passwordForm.formState.errors.password
                      ? 'border-red-400 focus:ring-red-400'
                      : 'border-gray-300'
                    }`}
                  placeholder="••••••••"
                  {...passwordForm.register('password')}
                />
                {passwordForm.formState.errors.password && (
                  <p id="central-password-error" className="mt-1 text-xs text-red-600">
                    {passwordForm.formState.errors.password.message}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                isLoading={isLoggingIn}
                fullWidth
                leftIcon={<LogIn size={16} />}
              >
                Ingresar
              </Button>
            </form>
          )}

          {/* Spinner de carga global (lookup en curso sin formulario visible) */}
          {isLookingUp && step !== 'email' && (
            <div className="flex justify-center py-4">
              <Spinner size="md" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
