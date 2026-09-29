import { apiClient } from '../../services/apiClient'

export interface PortalSubscription {
  id: string
  plan_name: string
  start_date: string
  end_date: string
  status: string
  total_amount: string
  paid_amount: string
  pending_amount: string
  remaining_meals: number
  remaining_days: number
  is_expiring: boolean
}

export interface TodaysMeal {
  id: string
  meal_name: string
  delivery_date: string
  status: string
  skippable: boolean
}

export interface PortalDashboardData {
  customer_name: string
  active_subscription: PortalSubscription | null
  todays_meal: TodaysMeal | null
  total_subscriptions: number
}

export interface PortalPayment {
  id: string
  amount: string
  method: string
  transaction_reference: string
  payment_date: string
  status: string
  subscription_plan: string
}

export interface PortalDelivery {
  id: string
  meal_name: string
  delivery_date: string
  status: string
  notes: string
}

export interface PortalProfile {
  id: string
  name: string
  phone: string
  email: string
  address: string
  location: string
}

function errMsg(e: unknown, fallback: string): string {
  const axiosErr = e as { response?: { data?: { error?: { message?: string } } } }
  return axiosErr?.response?.data?.error?.message || fallback
}

export const portalApi = {
  dashboard: () => apiClient.get<PortalDashboardData>('/portal/dashboard/'),

  subscriptions: () => apiClient.get<PortalSubscription[]>('/portal/subscriptions/'),

  payments: () => apiClient.get<PortalPayment[]>('/portal/payments/'),

  deliveries: () => apiClient.get<PortalDelivery[]>('/portal/deliveries/'),

  profile: () => apiClient.get<PortalProfile>('/portal/profile/'),

  updateProfile: (data: Partial<PortalProfile>) => apiClient.put<PortalProfile>('/portal/profile/', data),

  skipMeal: async (subId: string, date?: string, reason?: string) => {
    try {
      const { data } = await apiClient.post(`/portal/subscriptions/${subId}/skip/`, { date, reason })
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e, 'Could not skip meal') }
    }
  },

  pauseRequest: async (subId: string, startDate: string, endDate?: string, reason?: string) => {
    try {
      const { data } = await apiClient.post(`/portal/subscriptions/${subId}/pause-request/`, {
        start_date: startDate,
        end_date: endDate,
        reason,
      })
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e, 'Could not pause subscription') }
    }
  },

  renew: async (subId: string) => {
    try {
      const { data } = await apiClient.post(`/portal/subscriptions/${subId}/renew/`)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e, 'Could not renew subscription') }
    }
  },
}
