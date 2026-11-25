import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { AppRoutes } from './routes'
import { DialogHost } from '../components/ui/DialogHost'
import { ThemeSync } from '../components/ThemeSync'
import { useAppTheme } from '../hooks/useAppTheme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeSync />
        <AppRoutes />
        <ThemedToaster />
        <DialogHost />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

function ThemedToaster() {
  const dark = useAppTheme() !== null
  return (
    <Toaster
      position="top-center"
      richColors
      closeButton
      offset={16}
      theme={dark ? 'dark' : 'light'}
      toastOptions={{ duration: 3500 }}
    />
  )
}
