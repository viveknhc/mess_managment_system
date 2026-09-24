import { Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export function AdminLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-200 bg-white">
        <div className="flex h-16 items-center border-b border-gray-200 px-6">
          <h1 className="text-lg font-bold text-blue-600">Mess Manager</h1>
        </div>
        <nav className="p-4">
          <p className="text-sm text-gray-400">Navigation coming soon</p>
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
          <h2 className="text-lg font-semibold text-gray-800">Dashboard</h2>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user?.name || user?.username}
              <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                {user?.role}
              </span>
            </span>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto bg-gray-50">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
