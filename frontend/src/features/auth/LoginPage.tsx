/**
 * features/auth/LoginPage.tsx
 * ---------------------------
 * Pantalla de login (ruta pública: /login).
 * Formulario con React Hook Form + Zod.
 * Maneja estados: loading, error de credenciales, sin red.
 * Mobile-first, accesibilidad básica (labels, aria).
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { LogIn } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from './useAuth'
import { Button } from '@/components/Button'
import { ErrorState } from '@/components/ErrorState'
import logoUrl from '@/assets/logo.svg'

// ─── Schema de validación (Zod) ───────────────────────────────────────────────
// La validación dura (credenciales reales) la hace el backend.
// Aquí solo validamos formato básico para mejorar la UX.
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es obligatorio.')
    .email('Ingresá un email válido.'),
  password: z
    .string()
    .min(1, 'La contraseña es obligatoria.')
    .min(4, 'La contraseña es demasiado corta.'),
})

type LoginFormValues = z.infer<typeof loginSchema>

// ─── Componente ───────────────────────────────────────────────────────────────

export function LoginPage() {
  const { login, isLoggingIn, loginError } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = (data: LoginFormValues) => {
    login({ email: data.email, password: data.password })
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
          Ingresá a tu cuenta
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-sm rounded-2xl sm:px-8">
          {/* Error de login desde la API */}
          {loginError && (
            <div className="mb-5" role="alert">
              <ErrorState message={loginError} compact />
            </div>
          )}

          <form
            onSubmit={handleSubmit(onSubmit)}
            noValidate
            aria-label="Formulario de inicio de sesión"
          >
            {/* Campo: Email */}
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

            {/* Campo: Contraseña */}
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
                className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm
                  focus:outline-none focus:ring-2 focus:ring-brand-500
                  dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-400
                  ${errors.password
                    ? 'border-red-400 focus:ring-red-400'
                    : 'border-gray-300'
                  }`}
                placeholder="••••••••"
                {...register('password')}
              />
              {errors.password && (
                <p id="password-error" className="mt-1 text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Submit */}
            <Button
              type="submit"
              isLoading={isLoggingIn}
              fullWidth
              leftIcon={<LogIn size={16} />}
            >
              Ingresar
            </Button>
          </form>

          {/* Link recuperar contraseña */}
          <div className="mt-5 text-center">
            <Link
              to="/forgot-password"
              className="text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
