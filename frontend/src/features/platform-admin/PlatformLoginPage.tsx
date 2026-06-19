/**
 * features/platform-admin/PlatformLoginPage.tsx
 * -----------------------------------------------
 * Pantalla de login del panel de System Admin (ruta pública: /login).
 * Solo accesible desde platform.* — el routing condicional lo garantiza.
 *
 * Formulario con React Hook Form + Zod.
 * Estilo consistente con LoginPage del tenant.
 * Redirige a "/" (lista de tenants) tras login exitoso.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { LogIn, Shield } from 'lucide-react'
import { loginPlatform } from './platformAuthService'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'

// ─── Schema de validación ─────────────────────────────────────────────────────

const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es obligatorio.')
    .email('Ingresá un email válido.'),
  password: z.string().min(1, 'La contraseña es obligatoria.'),
})

type LoginFormValues = z.infer<typeof loginSchema>

// ─── Componente ───────────────────────────────────────────────────────────────

export function PlatformLoginPage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true)
    setLoginError(null)
    try {
      await loginPlatform(data.email, data.password)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'status' in err.response
      ) {
        const status = (err.response as { status: number }).status
        if (status === 401 || status === 400) {
          setLoginError(
            'Credenciales incorrectas o usuario sin permisos de plataforma.',
          )
        } else if (status >= 500) {
          setLoginError('Error del servidor. Intentá de nuevo en unos momentos.')
        } else {
          setLoginError('No se pudo iniciar sesión. Intentá de nuevo.')
        }
      } else {
        setLoginError('Sin conexión. Verificá tu red e intentá de nuevo.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
        {/* Logo / Marca */}
        <div className="flex justify-center">
          <div className="w-12 h-12 bg-gray-800 dark:bg-gray-700 rounded-xl flex items-center justify-center">
            <Shield className="text-white" size={24} aria-hidden="true" />
          </div>
        </div>
        <h1 className="mt-6 text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
          CANCHERO! — Plataforma
        </h1>
        <p className="mt-1 text-center text-sm text-gray-500 dark:text-gray-400">
          Panel de administración de la plataforma
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-sm rounded-2xl sm:px-8">
          {loginError && (
            <div className="mb-5" role="alert">
              <ErrorState message={loginError} compact />
            </div>
          )}

          <form
            onSubmit={handleSubmit(onSubmit)}
            noValidate
            aria-label="Formulario de inicio de sesión de plataforma"
          >
            {/* Email */}
            <div className="mb-4">
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
                className={[
                  'w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm',
                  'focus:outline-none focus:ring-2 focus:ring-gray-500',
                  'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400',
                  errors.email
                    ? 'border-red-400 focus:ring-red-400'
                    : 'border-gray-300',
                ].join(' ')}
                placeholder="superadmin@canchero.com"
                {...register('email')}
              />
              {errors.email && (
                <p id="email-error" className="mt-1 text-xs text-red-600">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Contraseña */}
            <div className="mb-6">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
              >
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={errors.password ? 'true' : 'false'}
                aria-describedby={errors.password ? 'password-error' : undefined}
                className={[
                  'w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm',
                  'focus:outline-none focus:ring-2 focus:ring-gray-500',
                  'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400',
                  errors.password
                    ? 'border-red-400 focus:ring-red-400'
                    : 'border-gray-300',
                ].join(' ')}
                placeholder="••••••••"
                {...register('password')}
              />
              {errors.password && (
                <p id="password-error" className="mt-1 text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>

            <Button
              type="submit"
              isLoading={isLoading}
              fullWidth
              leftIcon={<LogIn size={16} />}
              className="bg-gray-800 hover:bg-gray-900 text-white focus:ring-gray-700 disabled:bg-gray-300"
            >
              Ingresar a la plataforma
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
