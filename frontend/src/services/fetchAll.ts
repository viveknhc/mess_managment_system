import { apiClient } from './apiClient'

/**
 * Every row of a paginated list endpoint ({count, next, results}), following `next`.
 * For pickers/dropdowns that must offer the whole list — a single GET only returns
 * the first page (20 by default).
 */
export async function fetchAll<T>(url: string, params: Record<string, string> = {}): Promise<T[]> {
  const all: T[] = []
  for (let page = 1; ; page++) {
    const { data } = await apiClient.get(url, { params: { ...params, page, page_size: 100 } })
    all.push(...(data.results ?? data))
    if (!data.next) return all
  }
}
