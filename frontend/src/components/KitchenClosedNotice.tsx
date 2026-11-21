import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

/** JS getDay() is 0=Sunday; the backend uses Python's weekday(), 0=Monday … 6=Sunday. */
function weekday(date: Date) {
  return (date.getDay() + 6) % 7
}

function joinDays(days: number[]) {
  const names = days.map((d) => DAY_NAMES[d] + 's')
  return names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}` : names[0]
}

const RECHECK_MS = 5 * 60_000

/**
 * Today's date, re-read when the tab comes back into view so a page left open overnight
 * updates. Also re-reads the user (at most every 5 min) so a change the owner made to the
 * closed days reaches staff and customers without logging out.
 */
function useToday() {
  const refreshUser = useAuthStore((s) => s.refreshUser)
  const [today, setToday] = useState(() => new Date())
  useEffect(() => {
    let lastCheck = Date.now()
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      setToday(new Date())
      if (Date.now() - lastCheck > RECHECK_MS) {
        lastCheck = Date.now()
        refreshUser()
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [refreshUser])
  return today
}

function messages(role: string | undefined, dayName: string) {
  switch (role) {
    case 'CUSTOMER':
      return {
        today: `The mess is closed today (${dayName}). No meal today. You still get every meal in your plan.`,
        tomorrow: `The mess is closed tomorrow (${dayName}). No meal tomorrow.`,
      }
    case 'KITCHEN_STAFF':
      return {
        today: `Kitchen closed today (${dayName}). No meals to cook.`,
        tomorrow: `Kitchen closed tomorrow (${dayName}).`,
      }
    case 'DELIVERY_STAFF':
      return {
        today: `Kitchen closed today (${dayName}). No deliveries today.`,
        tomorrow: `Kitchen closed tomorrow (${dayName}). No deliveries tomorrow.`,
      }
    default:
      return {
        today: `Kitchen closed today (${dayName}). No meals are scheduled.`,
        tomorrow: `Kitchen closed tomorrow (${dayName}). No meals are scheduled.`,
      }
  }
}

/**
 * Status strip for every signed-in mess user, from the owner's "Kitchen closed on" setting:
 * an amber banner when the kitchen is closed today or tomorrow, otherwise a quiet line
 * naming the weekly closed days. Renders nothing for a mess that's open every day.
 */
export function KitchenClosedNotice() {
  const user = useAuthStore((s) => s.user)
  const today = useToday()
  const offDays = user?.kitchen_off_days ?? []
  if (!offDays.length) return null

  const todayIdx = weekday(today)
  const tomorrowIdx = (todayIdx + 1) % 7
  const closedToday = offDays.includes(todayIdx)
  const closedTomorrow = offDays.includes(tomorrowIdx)

  if (closedToday || closedTomorrow) {
    const msg = messages(user?.role, DAY_NAMES[closedToday ? todayIdx : tomorrowIdx])
    return (
      <div
        role="status"
        className={`border-b px-4 py-2.5 text-center text-sm font-medium ${
          closedToday ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-blue-100 bg-blue-50 text-blue-800'
        }`}
      >
        {closedToday ? msg.today : msg.tomorrow}
      </div>
    )
  }

  return (
    <div role="status" className="border-b border-gray-200 bg-gray-50 px-4 py-1.5 text-center text-xs text-gray-500">
      {user?.role === 'CUSTOMER' ? 'The mess is' : 'Kitchen'} closed on {joinDays(offDays)}
    </div>
  )
}
