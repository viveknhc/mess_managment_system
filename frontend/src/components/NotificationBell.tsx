import { useEffect, useState, useRef } from 'react'
import { apiClient } from '../services/apiClient'

interface Notification {
  id: string
  type: string
  title: string
  message: string
  is_read: boolean
  sent_at: string
}

export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  async function fetchData() {
    try {
      const [listRes, countRes] = await Promise.all([
        apiClient.get('/notifications/', { params: { page_size: 10 } }),
        apiClient.get('/notifications/unread_count/'),
      ])
      setNotifications(listRes.data.results)
      setUnreadCount(countRes.data.unread_count)
    } catch {
      // silent
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // poll every 30s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  async function handleMarkAllRead() {
    await apiClient.post('/notifications/mark_all_read/')
    await fetchData()
  }

  async function handleMarkRead(id: string) {
    await apiClient.post(`/notifications/${id}/mark_read/`)
    await fetchData()
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-gray-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="text-xs text-blue-600 hover:underline">
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-4 text-center text-sm text-gray-400">No notifications</p>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => !n.is_read && handleMarkRead(n.id)}
                  className={`block w-full border-b border-gray-50 px-4 py-3 text-left hover:bg-gray-50 ${
                    !n.is_read ? 'bg-blue-50/50' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {!n.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-blue-500" />}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{n.title}</p>
                      <p className="mt-0.5 truncate text-xs text-gray-500">{n.message}</p>
                      <p className="mt-1 text-[10px] text-gray-400">
                        {new Date(n.sent_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
