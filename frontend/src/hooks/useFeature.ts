import { useAuthStore } from '../store/authStore'

/** Feature keys — mirror backend/apps/customization/registry.py. SUPER_ADMIN turns them on/off per business. */
export const FEATURES = {
  CUSTOMER_PORTAL: 'customer_portal',
  ONLINE_PAYMENTS: 'online_payments',
  REPORTS: 'reports',
} as const

export type FeatureKey = (typeof FEATURES)[keyof typeof FEATURES]

export function useFeature(key: FeatureKey): boolean {
  return useAuthStore((s) => s.user?.features?.includes(key) ?? false)
}
