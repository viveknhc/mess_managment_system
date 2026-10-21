import { useMemo, useState } from 'react'
import { toOrdering, type SortState } from '../components/ui/DataTable'

/**
 * Page / page-size / sort state for a server-paginated DataTable.
 * `params` goes straight into `apiClient.get(url, { params: { ...table.params, ...filters } })`.
 * Changing sort or page size jumps back to page 1.
 */
export function useServerTable({ defaultSort = null, pageSize: initialPageSize = 20 }: { defaultSort?: SortState | null; pageSize?: number } = {}) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSizeState] = useState(initialPageSize)
  const [sort, setSortState] = useState<SortState | null>(defaultSort)

  const params = useMemo(() => {
    const p: Record<string, string> = { page: String(page), page_size: String(pageSize) }
    const ordering = toOrdering(sort)
    if (ordering) p.ordering = ordering
    return p
  }, [page, pageSize, sort])

  return {
    page,
    setPage,
    pageSize,
    setPageSize: (size: number) => {
      setPageSizeState(size)
      setPage(1)
    },
    sort,
    setSort: (s: SortState | null) => {
      setSortState(s)
      setPage(1)
    },
    params,
  }
}
