import type { PortalSubscription } from './portalApi'

/** "Your customizations" — the extras the mess set on this subscription (e.g. Extra chicken 100g). */
export function CustomizationChips({ sub }: { sub: PortalSubscription }) {
  if (!sub.items?.length) return null
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gray-500">Your customizations</p>
      <ul className="mt-1 flex flex-wrap gap-1.5">
        {sub.items.map((i) => (
          <li key={i.label} className="rounded-md border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-800">
            {i.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
