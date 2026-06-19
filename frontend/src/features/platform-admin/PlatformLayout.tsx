/**
 * features/platform-admin/PlatformLayout.tsx
 * --------------------------------------------
 * Layout del panel de platform (System Admin).
 * Compone PlatformNavBar + <Outlet /> de React Router.
 *
 * Padding-top/bottom igual que AdminLayout del tenant
 * para consistencia de espaciado.
 */

import { Outlet, useNavigate } from 'react-router-dom'
import { PlatformNavBar } from './PlatformNavBar'
import { getPlatformUser, logoutPlatform } from './platformAuthService'

export function PlatformLayout() {
  const navigate = useNavigate()
  const user = getPlatformUser()

  function handleLogout() {
    logoutPlatform()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <PlatformNavBar email={user?.email} onLogout={handleLogout} />
      <main className="pt-14 pb-16 md:pt-16 md:pb-0">
        <Outlet />
      </main>
    </div>
  )
}
