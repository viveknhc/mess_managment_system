import { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface Props {
  allowedRoles?: string[]
}

export function ProtectedRoute({ allowedRoles }: Props) {
  const { isAuthenticated, user, isLoading, fetchMe } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated && !user) {
      fetchMe()
    }
  }, [isAuthenticated, user, fetchMe])

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-sm text-gray-500">Loading...</div>
      </div>
    )
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Role-aware redirect
    if (user.role === 'SUPER_ADMIN') return <Navigate to="/platform" replace />
    if (user.role === 'CUSTOMER') return <Navigate to="/portal" replace />
    if (user.role === 'DELIVERY_STAFF' || user.role === 'KITCHEN_STAFF') return <Navigate to="/staff" replace />
    return <Navigate to="/app" replace />
  }

  return <Outlet />
}
