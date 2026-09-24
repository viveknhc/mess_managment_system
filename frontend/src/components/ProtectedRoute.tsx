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
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
