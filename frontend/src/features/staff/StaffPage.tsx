import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { StaffForm } from './StaffForm'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

interface Staff {
  id: string
  username: string
  name: string
  email: string
  phone: string
  role: string
  is_active: boolean
  date_joined: string
}

const ROLE_LABELS: Record<string, string> = {
  OWNER: 'Owner',
  MANAGER: 'Manager',
  DELIVERY_STAFF: 'Delivery',
  KITCHEN_STAFF: 'Kitchen',
}

export function StaffPage() {
  const [staff, setStaff] = useState<Staff[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Staff | null>(null)
  const table = useServerTable()
  const { params: tableParams } = table
  const user = useAuthStore((s) => s.user)
  const isOwner = user?.role === 'OWNER'

  const fetchStaff = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/staff/', { params: tableParams })
      setStaff(data.results)
      setCount(data.count)
    } catch {
      setError('Failed to load staff')
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchStaff()
  }, [fetchStaff])

  function handleEdit(s: Staff) {
    setEditing(s)
    setShowForm(true)
  }

  function handleAdd() {
    setEditing(null)
    setShowForm(true)
  }

  function handleClose() {
    setShowForm(false)
    setEditing(null)
  }

  async function handleSaved() {
    handleClose()
    await fetchStaff()
  }

  async function handleToggleActive(s: Staff) {
    try {
      const action = s.is_active ? 'deactivate' : 'activate'
      await apiClient.post(`/staff/${s.id}/${action}/`)
      await fetchStaff()
    } catch {
      setError(`Failed to ${s.is_active ? 'deactivate' : 'activate'} staff member`)
    }
  }

  const columns: Column<Staff>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: (s) => (
        <>
          <div className="font-medium text-gray-900">{s.name || s.username}</div>
          <div className="text-xs text-gray-500">@{s.username}</div>
        </>
      ),
    },
    {
      key: 'email',
      header: 'Contact',
      sortable: true,
      render: (s) => (
        <>
          <div className="text-gray-900">{s.email || '—'}</div>
          <div className="text-xs text-gray-500">{s.phone || '—'}</div>
        </>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      sortable: true,
      render: (s) => (
        <span className="inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          {ROLE_LABELS[s.role] || s.role}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      sortable: true,
      render: (s) => (
        <span
          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
            s.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {s.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'date_joined',
      header: 'Joined',
      sortable: true,
      className: 'whitespace-nowrap text-gray-500',
      render: (s) => s.date_joined.slice(0, 10),
    },
  ]

  if (isOwner) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (s) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => handleEdit(s)}
            className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
          >
            Edit
          </button>
          <button
            onClick={() => handleToggleActive(s)}
            className={`rounded px-2 py-1 text-xs font-medium ${
              s.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'
            }`}
          >
            {s.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      ),
    })
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Staff</h1>
          <p className="mt-1 text-sm text-gray-500">{count} member{count !== 1 ? 's' : ''}</p>
        </div>
        {isOwner && (
          <button
            onClick={handleAdd}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Add Staff
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {!loading && count === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No staff members yet</p>
          {isOwner && (
            <button
              onClick={handleAdd}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Add your first staff member
            </button>
          )}
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={staff}
          rowKey={(s) => s.id}
          loading={loading}
          rowClassName={(s) => (s.is_active ? '' : 'bg-gray-50 opacity-60')}
          sort={table.sort}
          onSortChange={table.setSort}
          pagination={{
            page: table.page,
            pageSize: table.pageSize,
            count,
            onPageChange: table.setPage,
            onPageSizeChange: table.setPageSize,
          }}
        />
      )}

      {showForm && <StaffForm staff={editing} onClose={handleClose} onSaved={handleSaved} />}
    </div>
  )
}
