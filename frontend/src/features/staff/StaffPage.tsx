import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { StaffForm } from './StaffForm'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'
import { notify } from '../../utils/notify'
import { confirmDialog } from '../../components/ui/dialog'
import { ActionButton } from '../../components/ui/ActionButton'
import { StatusBadge } from '../../components/ui/StatusBadge'

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
    if (s.is_active) {
      const ok = await confirmDialog({
        title: `Deactivate ${s.name || s.username}?`,
        message: 'They will no longer be able to log in. You can activate them again any time.',
        confirmText: 'Deactivate',
        tone: 'danger',
      })
      if (!ok) return
    }
    try {
      const action = s.is_active ? 'deactivate' : 'activate'
      await apiClient.post(`/staff/${s.id}/${action}/`)
      notify.success(s.is_active ? 'Staff member deactivated' : 'Staff member activated', s.name || s.username)
      await fetchStaff()
    } catch (err) {
      notify.error(err, `Failed to ${s.is_active ? 'deactivate' : 'activate'} staff member`)
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
      key: 'email', mobile: 'subtitle',
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
        <StatusBadge status={s.is_active ? 'ACTIVE' : 'INACTIVE'} label={s.is_active ? 'Active' : 'Inactive'} />
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
          <ActionButton tone="primary" onClick={() => handleEdit(s)}>
            Edit
          </ActionButton>
          <ActionButton
            onClick={() => handleToggleActive(s)}
            tone={s.is_active ? 'danger' : 'success'}
          >
            {s.is_active ? 'Deactivate' : 'Activate'}
          </ActionButton>
        </div>
      ),
    })
  }

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
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
