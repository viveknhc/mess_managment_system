import type { ReactNode } from 'react'
import { useFeature, type FeatureKey } from '../hooks/useFeature'

/** Renders children only when the business has the feature; otherwise a "not included" notice. */
export function FeatureGate({
  feature,
  message = "This feature isn't included for your mess. Contact MessDeck support to enable it.",
  children,
}: {
  feature: FeatureKey
  message?: string
  children: ReactNode
}) {
  const enabled = useFeature(feature)
  if (enabled) return <>{children}</>
  return (
    <div className="mx-auto max-w-md p-12 text-center">
      <h2 className="text-lg font-semibold text-gray-900">Not available</h2>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  )
}
