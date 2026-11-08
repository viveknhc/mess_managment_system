/**
 * Human-readable message from an API error envelope: {error: {code, message, fields}}.
 * Validation errors carry a generic message ("Request failed.") with the real reasons
 * in `fields` (e.g. {owner_username: ["Username already taken."]}) — prefer those.
 */
export function getApiErrorMessage(err: unknown, fallback = 'Something went wrong'): string {
  const error = (err as { response?: { data?: { error?: { message?: string; fields?: Record<string, string[] | string> } } } })
    ?.response?.data?.error
  const fieldMessages = Object.values(error?.fields ?? {}).flat().filter(Boolean)
  if (fieldMessages.length) return fieldMessages.join(' ')
  return error?.message || (err instanceof Error ? err.message : '') || fallback
}
