/**
 * features/auth/ResetPasswordPage.tsx
 * -------------------------------------
 * Pantalla de confirmación del reset de contraseña.
 * Ruta pública: /reset-password/:uid/:token
 *
 * Lee uid y token de los params del URL (React Router).
 * Formulario con dos campos: nueva contraseña y confirmación.
 *
 * Estados contemplados:
 *   - idle: formulario visible.
 *   - loading: botón deshabilitado.
 *   - success: mensaje de éxito + redirección automática a /login (2 seg).
 *   - error INVALID_RESET_LINK: mensaje específico con link a /forgot-password.
 *   - error genérico: banner de error.
 *
 * Mobile-first · mismos tokens visuales que LoginPage.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { KeyRound, ArrowLeft, CheckCircle } from 'lucide-react'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import { confirmPasswordReset } from '@/services/auth.service'
import logoUrl from '@/assets/logo.svg'

// ─── Schema ──────────────────────────────────────────────────────────────────

const resetPasswordSchema = z
  .object({
    new_password: z
      .string()
      .min(8, 'La contraseña debe tener al menos 8 caracteres.'),
    confirm_password: z
      .string()
      .min(1, 'Confirmá tu contraseña.'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Las contraseñas no coinciden.',
    path: ['confirm_password'],
  })

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>

// ─── Tipo de error ────────────────────────────────────────────────────────────

type ErrorKind = 'invalid_link' | 'generic' | null

// ─── Componente ──────────────────────────────────────────────────────────────

export function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [errorKind, setErrorKind] = useState<ErrorKind>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
  })

  const onSubmit = async (data: ResetPasswordFormValues) => {
    if (!uid || !token) {
      setErrorKind('invalid_link')
      return
    }

    setIsLoading(true)
    setErrorKind(null)

    try {
      await confirmPasswordReset(uid, token, data.new_password)
      setSuccess(true)
      // Redirigir a /login después de 2 segundos
      setTimeout(() => {
        navigate('/login', { replace: true })
      }, 2000)
    } catch (err: unknown) {
      // Detectar error de negocio INVALID_RESET_LINK (400 del backend)
      const isAxiosError =
        err !== null &&
        typeof err === 'object' &&
        'response' in err &&
        err.response !== null &&
        typeof err.response === 'object'

      if (isAxiosError) {
        const response = (err as { response: { status?: number; data?: { error?: { code?: string } } } }).response
        const status = response?.status
        const code = response?.data?.error?.code

        if (status === 400 && code === 'INVALID_RESET_LINK') {
          setErrorKind('invalid_link')
          return
        }
        // 400 sin código específico también puede ser link inválido
        if (status === 400) {
          setErrorKind('invalid_link')
          return
        }
      }

      setErrorKind('generic')
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
          Nueva contraseña
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-sm rounded-2xl sm:px-8">

          {/* ── Estado: éxito ──────────────────────────────────────────────── */}
          {success ? (
            <div className="text-center" role="status" aria-live="polite">
              <div className="flex justify-center mb-4">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <CheckCircle size={24} className="text-green-600 dark:text-green-400" aria-hidden="true" />
                </div>
              </div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                Contraseña actualizada
              </h2>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                Tu contraseña se cambió correctamente. Te redirigimos al inicio de sesión...
              </p>
            </div>
          ) : (
            /* ── Estado: formulario (idle / loading / error) ───────────────── */
            <>
              {/* Error: link inválido o expirado */}
              {errorKind === 'invalid_link' && (
                <div
                  className="mb-5 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-4"
                  role="alert"
                >
                  <p className="text-sm text-red-700 dark:text-red-400 font-medium">
                    El link es inválido o ya expiró.
                  </p>
                  <p className="mt-1 text-sm text-red-600 dark:text-red-500">
                    Solicitá un nuevo link desde la pantalla de recuperación.
                  </p>
                  <div className="mt-3">
                    <Link
                      to="/forgot-password"
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-red-700 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 underline underline-offset-2"
                    >
                      Solicitar nuevo link
                    </Link>
                  </div>
                </div>
              )}

              {/* Error: genérico */}
              {errorKind === 'generic' && (
                <div className="mb-5" role="alert">
                  <ErrorState
                    message="No pudimos actualizar tu contraseña. Revisá tu conexión e intentá de nuevo."
                    compact
                  />
                </div>
              )}

              <form
                onSubmit={handleSubmit(onSubmit)}
                noValidate
                aria-label="Formulario de nueva contraseña"
              >
                {/* Campo: Nueva contraseña */}
                <div className="mb-4">
                  <label
                    htmlFor="new_password"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                  >
                    Nueva contraseña
                  </label>
                  <input
                    id="new_password"
                    type="password"
                    autoComplete="new-password"
                    aria-invalid={errors.new_password ? 'true' : 'false'}
                    aria-describedby={errors.new_password ? 'new-password-error' : undefined}
                    className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm
                      focus:outline-none focus:ring-2 focus:ring-brand-500
                      dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400
                      ${errors.new_password
                        ? 'border-red-400 focus:ring-red-400'
                        : 'border-gray-300'
                      }`}
                    placeholder="Mínimo 8 caracteres"
                    {...register('new_password')}
                  />
                  {errors.new_password && (
                    <p id="new-password-error" className="mt-1 text-xs text-red-600">
                      {errors.new_password.message}
                    </p>
                  )}
                </div>

                {/* Campo: Confirmar contraseña */}
                <div className="mb-6">
                  <label
                    htmlFor="confirm_password"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                  >
                    Confirmar contraseña
                  </label>
                  <input
                    id="confirm_password"
                    type="password"
                    autoComplete="new-password"
                    aria-invalid={errors.confirm_password ? 'true' : 'false'}
                    aria-describedby={errors.confirm_password ? 'confirm-password-error' : undefined}
                    className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm
                      focus:outline-none focus:ring-2 focus:ring-brand-500
                      dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400
                      ${errors.confirm_password
                        ? 'border-red-400 focus:ring-red-400'
                        : 'border-gray-300'
                      }`}
                    placeholder="Repetí tu nueva contraseña"
                    {...register('confirm_password')}
                  />
                  {errors.confirm_password && (
                    <p id="confirm-password-error" className="mt-1 text-xs text-red-600">
                      {errors.confirm_password.message}
                    </p>
                  )}
                </div>

                {/* Submit */}
                <Button
                  type="submit"
                  isLoading={isLoading}
                  fullWidth
                  leftIcon={<KeyRound size={16} />}
                >
                  {isLoading ? 'Actualizando...' : 'Actualizar contraseña'}
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
