import { apiClient } from '../../services/apiClient'

export interface DeliveryItem {
  id: string
  customer_name: string
  customer_phone: string
  customer_address: string
  meal_name: string
  delivery_date: string
  status: string
  assigned_staff_name: string | null
  delivered_at: string | null
  notes: string
  updated_at: string
}

/** Quick-pick reasons when a meal can't be delivered (free text is allowed too). */
export const NOT_DELIVERED_REASONS = [
  'Customer not home',
  'Door locked',
  'Not answering phone',
  'Wrong address',
  'Customer refused',
]

export function isOpen(status: string) {
  return status === 'PENDING' || status === 'OUT_FOR_DELIVERY'
}

/** Matches backend deliveries.services.UNDO_WINDOW. */
const UNDO_WINDOW_MS = 10 * 60 * 1000

/** Can this Delivered / Not delivered mark still be undone? */
export function canUndo(d: DeliveryItem, now = Date.now()) {
  return (d.status === 'DELIVERED' || d.status === 'NOT_DELIVERED') && now - new Date(d.updated_at).getTime() < UNDO_WINDOW_MS
}

export function mapsLink(address: string) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
}

export const deliveryApi = {
  /** Every delivery for today, following pagination. */
  async allToday(): Promise<DeliveryItem[]> {
    const all: DeliveryItem[] = []
    for (let page = 1; ; page++) {
      const { data } = await apiClient.get('/deliveries/today/', {
        params: { page, page_size: 100, ordering: 'customer__name' },
      })
      all.push(...(data.results ?? data))
      if (!data.next) return all
    }
  },

  async setStatus(id: string, status: 'DELIVERED' | 'NOT_DELIVERED', notes = '') {
    const { data } = await apiClient.patch<DeliveryItem>(`/deliveries/${id}/status/`, { status, notes })
    return data
  },

  /** Back to PENDING — allowed for a few minutes after marking (backend UNDO_WINDOW). */
  async undo(id: string) {
    const { data } = await apiClient.post<DeliveryItem>(`/deliveries/${id}/undo/`)
    return data
  },

  async skip(id: string) {
    await apiClient.post(`/deliveries/${id}/skip/`)
  },
}
