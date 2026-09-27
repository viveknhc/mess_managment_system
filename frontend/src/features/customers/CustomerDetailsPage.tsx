import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '../../services/apiClient'
import { useAuthStore } from '../../store/authStore'
import { CustomerForm } from './CustomerForm'

interface CustomerDetail {
  id: string
  customer_code: string
  name: string
  phone: string
  email: string
  address: string
  location: string
  latitude: string | null
  longitude: string | null
  notes: string
  status: string
  created_at: string
  updated_at: string
}

export function CustomerDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [customer, setCustomer] = useState<CustomerDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const user = useAuthStore((s) => s.user)
  const canWrite = user?.role === 'OWNER' || user?.role === 'MANAGER'

  async function fetchCustomer() {
    setLoading(true)
    try {
      const { data } = await apiClient.get(`/customers/${id}/`)
      setCustomer(data)
    } catch {
      setError('Customer not found')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCustomer()
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleStatusChange(newStatus: string) {
    try {
      const { data } = await apiClient.patch(`/customers/${id}/`, { status: newStatus })
      setCustomer(data as CustomerDetail)
    } catch {
      setError('Failed to update status')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (error || !customer) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error || 'Customer not found'}</div>
        <button onClick={() => navigate('/customers')} className="mt-4 text-sm text-blue-600 hover:underline">
          Back to customers
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <button onClick={() => navigate('/customers')} className="mb-2 text-sm text-blue-600 hover:underline">
            &larr; Customers
          </button>
          <h1 className="text-xl font-bold text-gray-900">{customer.name}</h1>
          <p className="text-sm text-gray-500">{customer.customer_code}</p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              customer.status === 'ACTIVE'
                ? 'bg-green-50 text-green-700'
                : customer.status === 'BLOCKED'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-gray-100 text-gray-500'
            }`}
          >
            {customer.status}
          </span>
          {canWrite && (
            <button
              onClick={() => setEditing(true)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Info card */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <dl className="divide-y divide-gray-100 p-6">
          <div className="flex py-3 first:pt-0">
            <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Phone</dt>
            <dd className="text-sm text-gray-900">{customer.phone || '—'}</dd>
          </div>
          <div className="flex py-3">
            <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Email</dt>
            <dd className="text-sm text-gray-900">{customer.email || '—'}</dd>
          </div>
          <div className="flex py-3">
            <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Address</dt>
            <dd className="text-sm text-gray-900">{customer.address || '—'}</dd>
          </div>
          <div className="flex py-3">
            <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Location</dt>
            <dd className="text-sm text-gray-900">{customer.location || '—'}</dd>
          </div>
          {customer.notes && (
            <div className="flex py-3">
              <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Notes</dt>
              <dd className="text-sm text-gray-900 whitespace-pre-wrap">{customer.notes}</dd>
            </div>
          )}
          <div className="flex py-3 last:pb-0">
            <dt className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">Since</dt>
            <dd className="text-sm text-gray-900">
              {new Date(customer.created_at).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
              })}
            </dd>
          </div>
        </dl>
      </div>

      {/* Status actions */}
      {canWrite && (
        <div className="mt-4 flex gap-2">
          {customer.status !== 'ACTIVE' && (
            <button
              onClick={() => handleStatusChange('ACTIVE')}
              className="rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100"
            >
              Set Active
            </button>
          )}
          {customer.status !== 'BLOCKED' && (
            <button
              onClick={() => handleStatusChange('BLOCKED')}
              className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
            >
              Block
            </button>
          )}
          {customer.status !== 'INACTIVE' && (
            <button
              onClick={() => handleStatusChange('INACTIVE')}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200"
            >
              Set Inactive
            </button>
          )}
        </div>
      )}

      {/* Tabbed history — stub for now, populated when Subscriptions/Payments/Deliveries modules are built */}
      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">History</h2>
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-gray-400">
            Subscription, payment, and delivery history will appear here once those modules are built.
          </p>
        </div>
      </div>

      {editing && (
        <CustomerForm
          customer={customer}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            fetchCustomer()
          }}
        />
      )}
    </div>
  )
}
