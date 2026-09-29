import { Routes, Route, Navigate } from 'react-router-dom'
import { AdminLayout } from '../layouts/AdminLayout'
import { CustomerLayout } from '../layouts/CustomerLayout'
import { StaffLayout } from '../layouts/StaffLayout'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { LoginPage } from '../features/auth/LoginPage'
import { PortalDashboard } from '../features/portal/PortalDashboard'
import { PortalDeliveriesPage } from '../features/portal/PortalDeliveriesPage'
import { PortalPaymentsPage } from '../features/portal/PortalPaymentsPage'
import { PortalProfilePage } from '../features/portal/PortalProfilePage'
import { PortalSubscriptionPage } from '../features/portal/PortalSubscriptionPage'
import { CompletedDeliveriesPage } from '../features/deliveries/CompletedDeliveriesPage'
import { KitchenCountsPage } from '../features/deliveries/KitchenCountsPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { BusinessProfilePage } from '../features/business/BusinessProfilePage'
import { CustomersPage } from '../features/customers/CustomersPage'
import { CustomerDetailsPage } from '../features/customers/CustomerDetailsPage'
import { MealsPage } from '../features/meals/MealsPage'
import { PlansPage } from '../features/plans/PlansPage'
import { ReportsPage } from '../features/reports/ReportsPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { StaffPage } from '../features/staff/StaffPage'
import { TodayDeliveriesPage } from '../features/deliveries/TodayDeliveriesPage'
import { PaymentsPage } from '../features/payments/PaymentsPage'
import { SubscriptionsPage } from '../features/subscriptions/SubscriptionsPage'

export function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Admin routes — Owner + Manager */}
      <Route element={<ProtectedRoute allowedRoles={['OWNER', 'MANAGER', 'SUPER_ADMIN']} />}>
        <Route path="/" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="customers/:id" element={<CustomerDetailsPage />} />
          <Route path="meals" element={<MealsPage />} />
          <Route path="plans" element={<PlansPage />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="payments" element={<PaymentsPage />} />
          <Route path="deliveries" element={<TodayDeliveriesPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="staff" element={<StaffPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="business" element={<BusinessProfilePage />} />
        </Route>
      </Route>

      {/* Customer portal (PT-03–PT-06) */}
      <Route element={<ProtectedRoute allowedRoles={['CUSTOMER']} />}>
        <Route path="/portal" element={<CustomerLayout />}>
          <Route index element={<PortalDashboard />} />
          <Route path="subscription" element={<PortalSubscriptionPage />} />
          <Route path="meals" element={<PortalDeliveriesPage />} />
          <Route path="payments" element={<PortalPaymentsPage />} />
          <Route path="profile" element={<PortalProfilePage />} />
        </Route>
      </Route>

      {/* Staff routes — Delivery + Kitchen, role-aware nav (PT-07) */}
      <Route element={<ProtectedRoute allowedRoles={['DELIVERY_STAFF']} />}>
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<TodayDeliveriesPage />} />
          <Route path="completed" element={<CompletedDeliveriesPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['KITCHEN_STAFF']} />}>
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<KitchenCountsPage />} />
          <Route path="kitchen/summary" element={<KitchenCountsPage showSummary />} />
        </Route>
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
