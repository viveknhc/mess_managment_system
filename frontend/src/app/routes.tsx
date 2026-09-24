import { Routes, Route, Navigate } from 'react-router-dom'
import { AdminLayout } from '../layouts/AdminLayout'
import { CustomerLayout } from '../layouts/CustomerLayout'
import { StaffLayout } from '../layouts/StaffLayout'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { LoginPage } from '../features/auth/LoginPage'

export function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Admin routes — Owner + Manager */}
      <Route element={<ProtectedRoute allowedRoles={['OWNER', 'MANAGER', 'SUPER_ADMIN']} />}>
        <Route path="/" element={<AdminLayout />}>
          <Route index element={<div className="p-6 text-gray-500">Dashboard coming soon</div>} />
        </Route>
      </Route>

      {/* Customer portal */}
      <Route element={<ProtectedRoute allowedRoles={['CUSTOMER']} />}>
        <Route path="/portal" element={<CustomerLayout />}>
          <Route index element={<div className="p-6 text-gray-500">Customer portal coming soon</div>} />
        </Route>
      </Route>

      {/* Staff routes — Delivery + Kitchen */}
      <Route element={<ProtectedRoute allowedRoles={['DELIVERY_STAFF', 'KITCHEN_STAFF']} />}>
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<div className="p-6 text-gray-500">Staff view coming soon</div>} />
        </Route>
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
