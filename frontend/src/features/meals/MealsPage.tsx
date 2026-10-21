import { useCallback, useEffect, useState, type FormEvent, type ChangeEvent } from 'react'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { DataTable, type Column } from '../../components/ui/DataTable'
import { useServerTable } from '../../hooks/useServerTable'

interface Meal {
  id: string
  name: string
  description: string
  price: string | null
  is_active: boolean
}

export function MealsPage() {
  const [meals, setMeals] = useState<Meal[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Meal | null>(null)
  const [error, setError] = useState('')
  const table = useServerTable()
  const { params: tableParams } = table
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  const fetchMeals = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/meals/', { params: tableParams })
      setMeals(data.results)
      setCount(data.count)
    } catch {
      setError('Failed to load meals')
    } finally {
      setLoading(false)
    }
  }, [tableParams])

  useEffect(() => {
    fetchMeals()
  }, [fetchMeals])

  async function handleToggleActive(meal: Meal) {
    try {
      await apiClient.patch(`/meals/${meal.id}/`, { is_active: !meal.is_active })
      await fetchMeals()
    } catch {
      setError('Failed to update meal')
    }
  }

  const columns: Column<Meal>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: (meal) => (
        <>
          <div className="font-medium text-gray-900">{meal.name}</div>
          {meal.description && <div className="text-xs text-gray-500">{meal.description}</div>}
        </>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      align: 'right',
      className: 'font-medium text-gray-700',
      render: (meal) => (meal.price ? `₹${Number(meal.price).toFixed(2)}` : '—'),
    },
    {
      key: 'is_active',
      header: 'Status',
      sortable: true,
      render: (meal) => (
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            meal.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {meal.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
  ]

  if (canWrite) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (meal) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => {
              setEditing(meal)
              setShowForm(true)
            }}
            className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
          >
            Edit
          </button>
          <button
            onClick={() => handleToggleActive(meal)}
            className={`rounded px-2 py-1 text-xs font-medium ${
              meal.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'
            }`}
          >
            {meal.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      ),
    })
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Meals</h1>
          <p className="mt-1 text-sm text-gray-500">Meal types offered by your business</p>
        </div>
        {canWrite && (
          <button
            onClick={() => {
              setEditing(null)
              setShowForm(true)
            }}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Add Meal
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {!loading && count === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No meals yet</p>
          {canWrite && (
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Add your first meal
            </button>
          )}
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={meals}
          rowKey={(meal) => meal.id}
          loading={loading}
          rowClassName={(meal) => (meal.is_active ? '' : 'opacity-60')}
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

      {showForm && (
        <MealForm
          meal={editing}
          onClose={() => {
            setShowForm(false)
            setEditing(null)
          }}
          onSaved={() => {
            setShowForm(false)
            setEditing(null)
            fetchMeals()
          }}
        />
      )}
    </div>
  )
}

// ── Inline form modal ────────────────────────────────────────────────────

function MealForm({
  meal,
  onClose,
  onSaved,
}: {
  meal: Meal | null
  onClose: () => void
  onSaved: () => void
}) {
  const isEdit = !!meal
  const [form, setForm] = useState({
    name: meal?.name ?? '',
    description: meal?.description ?? '',
    price: meal?.price ?? '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function handleChange(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const payload = {
        name: form.name,
        description: form.description,
        price: form.price || null,
      }
      if (isEdit) {
        await apiClient.patch(`/meals/${meal.id}/`, payload)
      } else {
        await apiClient.post('/meals/', payload)
      }
      onSaved()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message || 'Failed to save'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-bold text-gray-900">
          {isEdit ? 'Edit Meal' : 'Add Meal'}
        </h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700">
              Name *
            </label>
            <input
              id="name"
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-medium text-gray-700">
              Description
            </label>
            <textarea
              id="description"
              name="description"
              value={form.description}
              onChange={handleChange}
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="price" className="mb-1 block text-sm font-medium text-gray-700">
              Price (₹)
            </label>
            <input
              id="price"
              name="price"
              type="number"
              step="0.01"
              min="0"
              value={form.price}
              onChange={handleChange}
              placeholder="Optional"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
