import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../services/apiClient'

const MAX_ROWS = 100

interface RowError {
  row: number
  errors: Record<string, string[]>
}

interface ImportErrorBody {
  code?: string
  message?: string
  fields?: { rows?: RowError[] } & Record<string, unknown>
}

interface Props {
  onClose: () => void
  onImported: (created: number) => void
}

function extractError(err: unknown): ImportErrorBody {
  const body = (err as { response?: { data?: { error?: ImportErrorBody } } })?.response?.data?.error
  return body ?? { message: 'Import failed. Please try again.' }
}

export function CustomerImportModal({ onClose, onImported }: Props) {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [templateError, setTemplateError] = useState('')

  const mutation = useMutation({
    mutationFn: async (f: File) => {
      const formData = new FormData()
      formData.append('file', f)
      const { data } = await apiClient.post<{ created: number }>('/customers/import/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      onImported(data.created)
    },
  })

  async function downloadTemplate() {
    setTemplateError('')
    try {
      const { data } = await apiClient.get<Blob>('/customers/import-template/', { responseType: 'blob' })
      const url = URL.createObjectURL(data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'customers_import_template.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setTemplateError('Could not download the template.')
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (file) mutation.mutate(file)
  }

  const error = mutation.isError ? extractError(mutation.error) : null
  const rowErrors = error?.fields?.rows ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-xl bg-white p-6 shadow-lg">
        <h2 className="mb-1 text-lg font-bold text-gray-900">Import Customers from CSV</h2>
        <p className="mb-4 text-sm text-gray-500">
          Upload a UTF-8 CSV with up to {MAX_ROWS} customers. <span className="font-medium">name</span> and{' '}
          <span className="font-medium">phone</span> are required; email, address, location and notes are optional.
          If any row has an error, nothing is imported.
        </p>

        <button
          type="button"
          onClick={downloadTemplate}
          className="mb-4 self-start text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline"
        >
          Download CSV template
        </button>
        {templateError && <p className="mb-4 text-sm text-red-600">{templateError}</p>}

        {error && (
          <div className="mb-4 overflow-y-auto rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            <p className="font-medium">{error.message || 'Import failed.'}</p>
            {rowErrors.length > 0 && (
              <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto">
                {rowErrors.map((r) => (
                  <li key={r.row}>
                    <span className="font-mono font-medium">Row {r.row}:</span>{' '}
                    {Object.entries(r.errors)
                      .map(([field, msgs]) => `${field} — ${msgs.join(' ')}`)
                      .join('; ')}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="csv-file" className="mb-1 block text-sm font-medium text-gray-700">
              CSV file
            </label>
            <input
              id="csv-file"
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null)
                mutation.reset()
              }}
              className="block w-full text-sm text-gray-700 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
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
              disabled={!file || mutation.isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Importing...' : 'Import'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
