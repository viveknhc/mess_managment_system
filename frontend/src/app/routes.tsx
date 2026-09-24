import { Routes, Route, Navigate } from 'react-router-dom'
import { AdminLayout } from '../layouts/AdminLayout'
import { CustomerLayout } from '../layouts/CustomerLayout'
import { StaffLayout } from '../layouts/StaffLayout'

export function AppRoutes() {
  return (
    <Routes>
      {/* Admin routes */}
      <Route path="/" element={<AdminLayout />}>
        <Route index element={<div className="p-6 text-gray-500">Dashboard coming soon</div>} />
      </Route>

      {/* Customer portal routes */}
      <Route path="/portal" element={<CustomerLayout />}>
        <Route index element={<div className="p-6 text-gray-500">Customer portal coming soon</div>} />
      </Route>

      {/* Staff routes */}
      <Route path="/staff" element={<StaffLayout />}>
        <Route index element={<div className="p-6 text-gray-500">Staff view coming soon</div>} />
      </Route>

      {/* Login placeholder */}
      <Route path="/login" element={<div className="flex h-screen items-center justify-center text-gray-500">Login page coming soon</div>} />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
