import { apiClient } from '../../services/apiClient'
import type { CheckoutStart, CheckoutSuccess } from '../../utils/razorpay'

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
  /** Food customizations agreed with the mess (feature custom_subscriptions). */
  items?: { label: string; price_per_meal: string }[]
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

/** Pay the mess's own UPI ID from any UPI app (mess confirms it later). */
export interface UpiPayStart {
  status: 'UPI'
  upi_url: string
  upi_id: string
  payee_name: string
  amount: string
  note: string
}

export interface UpiClaim {
  id: string
  subscription: string
  amount: string
  status: 'PENDING' | 'REJECTED'
  reject_reason: string
  created_at: string
}

export interface OnlinePaymentInfo {
  enabled: boolean
  /** RAZORPAY = automatic; UPI = customer pays the mess's UPI ID and the mess confirms. */
  mode: 'RAZORPAY' | 'UPI' | null
  upi_claims: UpiClaim[]
}

function errMsg(e: unknown, fallback: string): string {
  const axiosErr = e as { response?: { data?: { error?: { message?: string } } } }
  return axiosErr?.response?.data?.error?.message || fallback
}

export const portalApi = {
  dashboard: () => apiClient.get<PortalDashboardData>('/portal/dashboard/'),

  subscriptions: () => apiClient.get<PortalSubscription[]>('/portal/subscriptions/'),

  payments: () => apiClient.get<PortalPayment[]>('/portal/payments/'),

  onlinePayment: () => apiClient.get<OnlinePaymentInfo>('/portal/online-payment/'),

  startPayment: async (subId: string) => {
    try {
      const { data } = await apiClient.post<CheckoutStart | UpiPayStart>(`/portal/subscriptions/${subId}/pay/`)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e, 'Could not start the payment') }
    }
  },

  verifyPayment: async (subId: string, result: CheckoutSuccess) => {
    try {
      const { data } = await apiClient.post(`/portal/subscriptions/${subId}/pay/verify/`, result)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e, 'Could not confirm the payment') }
    }
  },

  /** "I've paid by UPI" — the mess confirms it after checking their account. */
  claimUpi: async (subId: string, utr: string) => {
    try {
      const { data } = await apiClient.post(`/portal/subscriptions/${subId}/pay/upi-claim/`, { utr })
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e, 'Could not send your payment details') }
    }
  },

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
