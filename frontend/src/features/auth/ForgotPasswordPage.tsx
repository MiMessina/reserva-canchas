/**
 * features/auth/ForgotPasswordPage.tsx
 * -------------------------------------
 * Pantalla de recuperación de contraseña (ruta pública: /forgot-password).
 * El jugador ingresa su email y recibe las instrucciones por correo.
 *
 * Estados contemplados:
 *   - idle: formulario visible.
 *   - loading: botón deshabilitado con "Enviando...".
 *   - success: oculta el formulario, muestra mensaje de éxito.
 *   - error: banner de error genérico (no se revela si el email existe o no).
 *
 * Mobile-first · mismos tokens visuales que LoginPage.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { ArrowLeft, Mail } from 'lucide-react'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { requestPasswordReset } from '@/services/auth.service'
import logoUrl from '@/assets/logo.svg'

// ─── Schema ──────────────────────────────────────────────────────────────────

const forgotPasswordSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es obligatorio.')
    .email('Ingresá un email válido.'),
})

type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>

// ─── Componente ──────────────────────────────────────────────────────────────

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  const onSubmit = async (data: ForgotPasswordFormValues) => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      await requestPasswordReset(data.email)
      setSubmitted(true)
    } catch {
      setErrorMessage(
        'No pudimos procesar tu solicitud. Revisá tu conexión e intentá de nuevo.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
        {/* Logo / Marca */}
        <div className="flex justify-center">
          <img src={logoUrl} alt="CANCHERO!" className="w-12 h-12" />
        </div>
        <h1 className="mt-6 text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
          CANCHERO!
        </h1>
        <p className="mt-1 text-center text-sm text-gray-500 dark:text-gray-400">
          Recuperar contraseña
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-sm rounded-2xl sm:px-8">

          {/* ── Estado: éxito ──────────────────────────────────────────────── */}
          {submitted ? (
            <div className="text-center" role="status" aria-live="polite">
              <div className="flex justify-center mb-4">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <Mail size={24} className="text-green-600 dark:text-green-400" aria-hidden="true" />
                </div>
              </div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                ¡Revisá tu correo!
              </h2>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                Si el email está registrado, recibirás las instrucciones en breve. Revisá tu bandeja.
              </p>
              <div className="mt-6">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 font-medium"
                >
                  <ArrowLeft size={14} aria-hidden="true" />
                  Volver al inicio de sesión
                </Link>
              </div>
            </div>
          ) : (
            /* ── Estado: formulario (idle / loading / error) ───────────────── */
            <>
              <p className="mb-5 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                Ingresá tu email y te enviaremos un link para restablecer tu contraseña.
              </p>

              {/* Error de la API */}
              {errorMessage && (
                <div className="mb-5" role="alert">
                  <ErrorState message={errorMessage} compact />
                </div>
              )}

              <form
                onSubmit={handleSubmit(onSubmit)}
                noValidate
                aria-label="Formulario de recuperación de contraseña"
              >
                {/* Campo: Email */}
                <div className="mb-6">
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    inputMode="email"
                    aria-invalid={errors.email ? 'true' : 'false'}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                    className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm
                      focus:outline-none focus:ring-2 focus:ring-brand-500
                      dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400
                      ${errors.email
                        ? 'border-red-400 focus:ring-red-400'
                        : 'border-gray-300'
                      }`}
                    placeholder="tu@email.com"
                    {...register('email')}
                  />
                  {errors.email && (
                    <p id="email-error" className="mt-1 text-xs text-red-600">
                      {errors.email.message}
                    </p>
                  )}
                </div>

                {/* Submit */}
                <Button
                  type="submit"
                  isLoading={isLoading}
                  fullWidth
                  leftIcon={<Mail size={16} />}
                >
                  {isLoading ? 'Enviando...' : 'Enviar instrucciones'}
                </Button>
              </form>

              {/* Link volver */}
              <div className="mt-5 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <ArrowLeft size={14} aria-hidden="true" />
                  Volver al inicio de sesión
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
