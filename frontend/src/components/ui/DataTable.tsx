import { isValidElement, useMemo, useState, type ReactNode } from 'react'
import { nextSort, type SortDir, type SortState } from './tableSort'
import { MOBILE_QUERY, useMediaQuery } from '../../hooks/useMediaQuery'

export type { SortDir, SortState }

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
  /**
   * Where this column goes in the phone card view (screens under 768px):
   * - title: the card heading (default: the first column)
   * - subtitle: a line under the heading
   * - badge: top-right pill (default for `status`, `is_active`, `…__status` columns)
   * - actions: button row at the bottom (default for the `actions` column)
   * - field: a small "label  value" pair (default)
   * - hidden: left out on phones
   */
  mobile?: 'title' | 'subtitle' | 'badge' | 'actions' | 'field' | 'hidden'
  /** Card label when the header isn't plain text. */
  mobileLabel?: string
}

type MobileRole = NonNullable<Column<unknown>['mobile']>

function mobileRoles<T>(columns: Column<T>[]): MobileRole[] {
  const hasTitle = columns.some((c) => c.mobile === 'title')
  return columns.map((c, i) => {
    if (c.mobile) return c.mobile
    if (c.key === 'actions') return 'actions'
    if (c.key === 'status' || c.key === 'is_active' || c.key.endsWith('__status')) return 'badge'
    if (!hasTitle && i === 0) return 'title'
    return 'field'
  })
}

/** Nothing worth a card slot: empty, or just a placeholder dash (also when wrapped, e.g. <span>—</span>). */
function isEmpty(node: ReactNode): boolean {
  if (node === null || node === undefined || node === false) return true
  if (typeof node === 'string') return ['', '—', '-', '–'].includes(node.trim())
  if (isValidElement<{ children?: ReactNode }>(node)) {
    const kids = node.props.children
    return kids !== undefined && !Array.isArray(kids) && isEmpty(kids)
  }
  return false
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
  const isMobile = useMediaQuery(MOBILE_QUERY)
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

  const pager = pagination && pagination.count > 0 && (
    <Pager pagination={pagination} firstRow={firstRow} lastRow={lastRow} totalPages={totalPages} />
  )

  if (isMobile) {
    return (
      <div>
        <CardList
          columns={columns}
          rows={sortedRows}
          rowKey={rowKey}
          sort={sort}
          onSort={(next) => (isServer ? onSortChange(next) : setLocalSort(next))}
          loading={loading}
          emptyMessage={emptyMessage}
          onRowClick={onRowClick}
          rowClassName={rowClassName}
        />
        {pager}
      </div>
    )
  }

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
                    <td key={col.key} className={`px-4 py-3 text-sm max-sm:whitespace-nowrap ${ALIGN[col.align ?? 'left']} ${col.className ?? ''}`}>
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pager}
    </div>
  )
}

function Pager({ pagination, firstRow, lastRow, totalPages }: {
  pagination: Pagination; firstRow: number; lastRow: number; totalPages: number
}) {
  return (

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
  )
}

/** Phone view: one card per row instead of a wide table. */
function CardList<T>({ columns, rows, rowKey, sort, onSort, loading, emptyMessage, onRowClick, rowClassName }: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  sort: SortState | null
  onSort: (next: SortState | null) => void
  loading: boolean
  emptyMessage: ReactNode
  onRowClick?: (row: T) => void
  rowClassName?: (row: T) => string
}) {
  const roles = mobileRoles(columns)
  const pick = (role: MobileRole) => columns.filter((_, i) => roles[i] === role)
  const [title, subtitles, badges, fields, actions] = [
    pick('title'), pick('subtitle'), pick('badge'), pick('field'), pick('actions'),
  ]
  const label = (c: Column<T>) => c.mobileLabel ?? (typeof c.header === 'string' ? c.header : c.key)
  const sortable = columns.filter((c) => c.sortable)

  return (
    <div>
      {sortable.length > 0 && (
        <label className="mb-2 flex items-center justify-end gap-2 text-xs text-gray-500">
          Sort by
          <select
            value={sort ? `${sort.key}:${sort.dir}` : ''}
            onChange={(e) => {
              const [key, dir] = e.target.value.split(':')
              onSort(key ? { key, dir: dir as SortDir } : null)
            }}
            className="rounded-full border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-800 focus:border-blue-500 focus:outline-none"
          >
            <option value="">Default</option>
            {sortable.map((c) => (
              <optgroup key={c.key} label={label(c)}>
                <option value={`${c.key}:asc`}>{label(c)} ↑</option>
                <option value={`${c.key}:desc`}>{label(c)} ↓</option>
              </optgroup>
            ))}
          </select>
        </label>
      )}

      {loading && rows.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-12">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-10 text-center text-sm text-gray-500">{emptyMessage}</div>
      ) : (
        <ul className={`space-y-2 transition-opacity ${loading ? 'opacity-50' : ''}`}>
          {rows.map((row) => {
            const shownFields = fields.map((c) => [c, c.render(row)] as const).filter(([, v]) => !isEmpty(v))
            const shownActions = actions.map((c) => c.render(row)).filter((v) => !isEmpty(v))
            return (
              <li
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`rounded-xl border border-gray-200 bg-white px-3 py-2.5 ${onRowClick ? 'cursor-pointer active:bg-gray-50' : ''} ${rowClassName?.(row) ?? ''}`}
              >
                {/* name · subtitle ………… badge, all on one line */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 flex-1 items-baseline gap-1.5 text-sm">
                    {title.map((c) => (
                      <span key={c.key} className="shrink-0 font-medium text-gray-900 [&_*]:inline [&>*+*]:ml-1.5 [&_div+div]:ml-1.5 [&_p+p]:ml-1.5">{c.render(row)}</span>
                    ))}
                    {subtitles.map((c) => {
                      const v = c.render(row)
                      return isEmpty(v) ? null : (
                        <span key={c.key} className="min-w-0 truncate text-xs text-gray-500 [&_*]:inline [&>*+*]:ml-1.5 [&_div+div]:ml-1.5 [&_p+p]:ml-1.5">· {v}</span>
                      )
                    })}
                  </div>
                  {badges.length > 0 && (
                    <div className="flex shrink-0 items-center gap-1">
                      {badges.map((c) => <span key={c.key}>{c.render(row)}</span>)}
                    </div>
                  )}
                </div>

                {/* label value · label value … wrapping inline */}
                {shownFields.length > 0 && (
                  <dl className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs leading-5">
                    {shownFields.map(([c, v]) => (
                      <div key={c.key} className="flex min-w-0 items-baseline gap-1">
                        <dt className="text-gray-500">{label(c)}</dt>
                        <dd className="text-gray-800 [overflow-wrap:anywhere] [&_div]:inline [&_p]:inline [&>*+*]:ml-1.5 [&_div+div]:ml-1.5 [&_p+p]:ml-1.5 [&_span]:align-baseline">{v}</dd>
                      </div>
                    ))}
                  </dl>
                )}

                {shownActions.length > 0 && (
                  // Buttons act on their own; a tap here must not also open the row.
                  <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs" onClick={(e) => e.stopPropagation()}>
                    {shownActions.map((v, i) => <div key={i}>{v}</div>)}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
