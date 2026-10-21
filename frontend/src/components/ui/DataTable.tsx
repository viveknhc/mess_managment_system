import { useMemo, useState, type ReactNode } from 'react'

export type SortDir = 'asc' | 'desc'
export interface SortState {
  key: string
  dir: SortDir
}

type SortPrimitive = string | number | boolean | null | undefined

export interface Column<T> {
  /** Unique column id. In server mode this is also the `?ordering=` field (e.g. `customer__name`). */
  key: string
  header: ReactNode
  render: (row: T) => ReactNode
  /** Make the column header clickable. */
  sortable?: boolean
  /** Client mode: value to sort by. Defaults to `row[key]`. */
  sortValue?: (row: T) => SortPrimitive
  align?: 'left' | 'right' | 'center'
  /** Extra classes for the body cell. */
  className?: string
}

export interface Pagination {
  page: number
  pageSize: number
  count: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (size: number) => void
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  /**
   * Server mode: pass `sort` + `onSortChange` — rows are rendered as given and the
   * parent refetches with `?ordering=`. Client mode: omit both — rows are sorted here.
   */
  sort?: SortState | null
  onSortChange?: (sort: SortState | null) => void
  /** Client mode only: initial sort. */
  defaultSort?: SortState | null
  pagination?: Pagination
  loading?: boolean
  emptyMessage?: ReactNode
  onRowClick?: (row: T) => void
  rowClassName?: (row: T) => string
}

const PAGE_SIZES = [10, 20, 50, 100]
const ALIGN = { left: 'text-left', right: 'text-right', center: 'text-center' } as const
const JUSTIFY = { left: 'justify-start', right: 'justify-end', center: 'justify-center' } as const

/** asc → desc → off */
export function nextSort(current: SortState | null | undefined, key: string): SortState | null {
  if (!current || current.key !== key) return { key, dir: 'asc' }
  if (current.dir === 'asc') return { key, dir: 'desc' }
  return null
}

export function toOrdering(sort: SortState | null | undefined): string | undefined {
  if (!sort) return undefined
  return sort.dir === 'desc' ? `-${sort.key}` : sort.key
}

function compare(a: SortPrimitive, b: SortPrimitive): number {
  const aEmpty = a === null || a === undefined || a === ''
  const bEmpty = b === null || b === undefined || b === ''
  if (aEmpty || bEmpty) return aEmpty === bEmpty ? 0 : aEmpty ? 1 : -1 // blanks last
  if (typeof a === 'number' && typeof b === 'number') return a - b
  if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b)
  // Numeric-looking strings (DRF decimals like "2500.00") compare as numbers.
  const na = Number(a)
  const nb = Number(b)
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' })
}

function SortIcon({ dir }: { dir: SortDir | null }) {
  return (
    <svg viewBox="0 0 10 14" className="h-3 w-2.5 shrink-0" aria-hidden="true">
      <path d="M5 1 L9 5.5 H1 Z" className={dir === 'asc' ? 'fill-blue-600' : 'fill-gray-300'} />
      <path d="M5 13 L1 8.5 H9 Z" className={dir === 'desc' ? 'fill-blue-600' : 'fill-gray-300'} />
    </svg>
  )
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  sort: controlledSort,
  onSortChange,
  defaultSort = null,
  pagination,
  loading = false,
  emptyMessage = 'No records found',
  onRowClick,
  rowClassName,
}: Props<T>) {
  const isServer = onSortChange !== undefined
  const [localSort, setLocalSort] = useState<SortState | null>(defaultSort)
  const sort = isServer ? (controlledSort ?? null) : localSort

  const sortedRows = useMemo(() => {
    if (isServer || !sort) return rows
    const col = columns.find((c) => c.key === sort.key)
    if (!col) return rows
    const get = col.sortValue ?? ((r: T) => (r as Record<string, SortPrimitive>)[col.key])
    const factor = sort.dir === 'asc' ? 1 : -1
    // Blanks stay last in both directions.
    return [...rows].sort((a, b) => {
      const va = get(a)
      const vb = get(b)
      const aEmpty = va === null || va === undefined || va === ''
      const bEmpty = vb === null || vb === undefined || vb === ''
      if (aEmpty || bEmpty) return compare(va, vb)
      return compare(va, vb) * factor
    })
  }, [isServer, sort, rows, columns])

  function handleSort(key: string) {
    const next = nextSort(sort, key)
    if (isServer) onSortChange(next)
    else setLocalSort(next)
  }

  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.count / pagination.pageSize)) : 1
  const firstRow = pagination && pagination.count > 0 ? (pagination.page - 1) * pagination.pageSize + 1 : 0
  const lastRow = pagination ? Math.min(pagination.page * pagination.pageSize, pagination.count) : 0

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              {columns.map((col) => {
                const align = col.align ?? 'left'
                const active = sort?.key === col.key ? sort.dir : null
                return (
                  <th
                    key={col.key}
                    scope="col"
                    aria-sort={active === 'asc' ? 'ascending' : active === 'desc' ? 'descending' : undefined}
                    className={`px-4 py-3 text-xs font-medium tracking-wide whitespace-nowrap text-gray-500 uppercase ${ALIGN[align]}`}
                  >
                    {col.sortable ? (
                      <button
                        type="button"
                        onClick={() => handleSort(col.key)}
                        title={active === 'asc' ? 'Sorted ascending — click for descending' : active === 'desc' ? 'Sorted descending — click to clear' : 'Click to sort'}
                        className={`inline-flex w-full items-center gap-1.5 uppercase hover:text-gray-900 ${JUSTIFY[align]} ${active ? 'text-gray-900' : ''}`}
                      >
                        {col.header}
                        <SortIcon dir={active} />
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody className={`divide-y divide-gray-100 transition-opacity ${loading && rows.length > 0 ? 'opacity-50' : ''}`}>
            {loading && rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-12">
                  <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
                </td>
              </tr>
            ) : sortedRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-12 text-center text-sm text-gray-500">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sortedRows.map((row) => (
                <tr
                  key={rowKey(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={`${onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''} ${rowClassName?.(row) ?? ''}`}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={`px-4 py-3 text-sm ${ALIGN[col.align ?? 'left']} ${col.className ?? ''}`}>
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && pagination.count > 0 && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-gray-500">
          <div className="flex items-center gap-3">
            <span>
              Showing {firstRow}–{lastRow} of {pagination.count}
            </span>
            {pagination.onPageSizeChange && (
              <label className="flex items-center gap-1.5">
                <span>Rows</span>
                <select
                  value={pagination.pageSize}
                  onChange={(e) => pagination.onPageSizeChange!(Number(e.target.value))}
                  className="rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                >
                  {PAGE_SIZES.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <span>
                Page {pagination.page} of {totalPages}
              </span>
              <button
                onClick={() => pagination.onPageChange(Math.max(1, pagination.page - 1))}
                disabled={pagination.page === 1}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => pagination.onPageChange(Math.min(totalPages, pagination.page + 1))}
                disabled={pagination.page >= totalPages}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
