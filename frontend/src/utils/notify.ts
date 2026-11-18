import { toast } from 'sonner'
import { getApiErrorMessage } from './apiError'

/** App-wide toast notifications (sonner). <Toaster /> is mounted once in App. */
export const notify = {
  success: (message: string, description?: string) => toast.success(message, { description }),
  info: (message: string, description?: string) => toast(message, { description }),
  /** Shows the API's error message when there is one, else `fallback`. */
  error: (err: unknown, fallback = 'Something went wrong') =>
    toast.error(typeof err === 'string' ? err : getApiErrorMessage(err, fallback)),
  /** Success toast with an Undo button. */
  undoable: (message: string, onUndo: () => void, description?: string) =>
    toast.success(message, { description, duration: 8000, action: { label: 'Undo', onClick: onUndo } }),
}
