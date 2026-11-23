import { apiClient } from '../../services/apiClient'

/** A delivery route (feature delivery_routes): customers delivered by one staff member. */
export interface DeliveryRoute {
  id: string
  name: string
  staff: string | null
  staff_name: string | null
  notes: string
  customer_count: number
  customers: { id: string; name: string; customer_code: string; location: string }[]
}

export interface RouteInput {
  name: string
  staff: string | null
  notes: string
  /** The route's full customer list — customers left out are taken off it. */
  customer_ids: string[]
}

export const routeApi = {
  async list(): Promise<DeliveryRoute[]> {
    const { data } = await apiClient.get<DeliveryRoute[]>('/delivery-routes/')
    return data
  },
  async create(input: RouteInput) {
    const { data } = await apiClient.post<DeliveryRoute>('/delivery-routes/', input)
    return data
  },
  async update(id: string, input: RouteInput) {
    const { data } = await apiClient.patch<DeliveryRoute>(`/delivery-routes/${id}/`, input)
    return data
  },
  async remove(id: string) {
    await apiClient.delete(`/delivery-routes/${id}/`)
  },
}
