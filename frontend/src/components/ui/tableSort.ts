export type SortDir = 'asc' | 'desc'
export interface SortState {
  key: string
  dir: SortDir
}

/** asc → desc → off */
export function nextSort(current: SortState | null | undefined, key: string): SortState | null {
  if (!current || current.key !== key) return { key, dir: 'asc' }
  if (current.dir === 'asc') return { key, dir: 'desc' }
  return null
}

/** SortState → DRF `?ordering=` value. */
export function toOrdering(sort: SortState | null | undefined): string | undefined {
  if (!sort) return undefined
  return sort.dir === 'desc' ? `-${sort.key}` : sort.key
}
