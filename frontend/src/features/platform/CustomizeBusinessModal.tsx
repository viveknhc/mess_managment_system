import { useEffect, useState } from 'react'
import {
  platformApi,
  type BusinessCustomization,
  type BusinessCustomizationUpdate,
  type CatalogPolicy,
  type CustomizationCatalog,
  type PlatformBusiness,
  type PolicyParam,
} from './platformApi'
import { notify } from '../../utils/notify'

/** Per-feature choice: follow the plan, or force on/off for this business only. */
type FeatureChoice = 'inherit' | 'on' | 'off'
type PolicyChoice = { policy: string; params: Record<string, unknown> }

function featureChoices(data: BusinessCustomization): Record<string, FeatureChoice> {
  return Object.fromEntries(
    data.features.map((f) => [f.key, f.source === 'override' ? (f.enabled ? 'on' : 'off') : 'inherit']),
  )
}

function policyChoices(data: BusinessCustomization): Record<string, PolicyChoice> {
  return Object.fromEntries(data.policies.map((p) => [p.point, { policy: p.policy, params: p.params }]))
}

function defaultParams(policy: CatalogPolicy | undefined): Record<string, unknown> {
  return Object.fromEntries((policy?.params ?? []).map((p) => [p.name, p.default ?? '']))
}

function ParamInput({ param, value, onChange }: { param: PolicyParam; value: unknown; onChange: (v: unknown) => void }) {
  if (param.type === 'boolean') {
    return (
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        {param.label}
      </label>
    )
  }
  const numeric = param.type === 'integer' || param.type === 'decimal' || param.type === 'float'
  return (
    <label className="block text-xs text-gray-600">
      {param.label}
      <input
        type={numeric ? 'number' : 'text'}
        required={param.required}
        value={value === null || value === undefined ? '' : String(value)}
        onChange={(e) => onChange(numeric && e.target.value !== '' ? Number(e.target.value) : e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      />
    </label>
  )
}

export function CustomizeBusinessModal({ biz, onClose }: { biz: Pick<PlatformBusiness, 'id' | 'name'>; onClose: () => void }) {
  const [catalog, setCatalog] = useState<CustomizationCatalog | null>(null)
  const [current, setCurrent] = useState<BusinessCustomization | null>(null)
  const [features, setFeatures] = useState<Record<string, FeatureChoice>>({})
  const [policies, setPolicies] = useState<Record<string, PolicyChoice>>({})
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([platformApi.getCustomizationCatalog(), platformApi.getBusinessCustomization(biz.id)])
      .then(([cat, data]) => {
        setCatalog(cat)
        setCurrent(data)
        setFeatures(featureChoices(data))
        setPolicies(policyChoices(data))
      })
      .catch(() => setError('Could not load customization.'))
  }, [biz.id])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!current) return
    // Send only what changed, so the audit log records real changes.
    const before = { features: featureChoices(current), policies: policyChoices(current) }
    const update: BusinessCustomizationUpdate = { features: {}, policies: {} }
    for (const [key, choice] of Object.entries(features)) {
      if (choice !== before.features[key]) update.features![key] = choice === 'inherit' ? null : choice === 'on'
    }
    for (const [point, choice] of Object.entries(policies)) {
      if (JSON.stringify(choice) !== JSON.stringify(before.policies[point])) update.policies![point] = choice
    }
    setSaving(true)
    setError('')
    const result = await platformApi.updateBusinessCustomization(biz.id, update)
    setSaving(false)
    if (!result.ok) {
      setError(result.error)
      return
    }
    setCurrent(result.data)
    setFeatures(featureChoices(result.data))
    setPolicies(policyChoices(result.data))
    notify.success('Customization saved', biz.name)
  }

  const inherited = Object.fromEntries((current?.features ?? []).map((f) => [f.key, f]))

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 sm:items-center sm:p-4">
      <div className="max-h-[92dvh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-xl sm:p-6">
        <h2 className="text-lg font-bold text-gray-900">Customize {biz.name}</h2>
        <p className="mt-1 text-sm text-gray-500">
          Choose what this mess gets and how its workflows run. Changes apply to this mess only and take
          effect the next time its users load the app.
        </p>
        {error && <div role="alert" className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>}

        {!catalog || !current ? (
          !error && <p className="mt-6 text-sm text-gray-500">Loading...</p>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-6">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Features</h3>
              <div className="mt-2 divide-y divide-gray-100 rounded-lg border border-gray-200">
                {catalog.features.map((f) => {
                  const base = inherited[f.key]
                  const followLabel = `Follow ${base?.source === 'plan' ? 'plan' : 'default'} (${base?.inherited ? 'on' : 'off'})`
                  return (
                    <div key={f.key} className="flex items-center justify-between gap-4 p-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{f.label}</p>
                        <p className="text-xs text-gray-500">{f.description}</p>
                      </div>
                      <select
                        aria-label={f.label}
                        value={features[f.key] ?? 'inherit'}
                        onChange={(e) => setFeatures({ ...features, [f.key]: e.target.value as FeatureChoice })}
                        className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
                      >
                        <option value="inherit">{followLabel}</option>
                        <option value="on">On for this mess</option>
                        <option value="off">Off for this mess</option>
                      </select>
                    </div>
                  )
                })}
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Workflows</h3>
              <div className="mt-2 space-y-3">
                {catalog.extension_points.map((point) => {
                  const choice = policies[point.key] ?? { policy: point.default, params: {} }
                  const selected = point.policies.find((p) => p.key === choice.policy)
                  return (
                    <div key={point.key} className="rounded-lg border border-gray-200 p-3">
                      <label className="block text-sm font-medium text-gray-900">
                        {point.label}
                        <select
                          value={choice.policy}
                          onChange={(e) => {
                            const policy = point.policies.find((p) => p.key === e.target.value)
                            setPolicies({ ...policies, [point.key]: { policy: e.target.value, params: defaultParams(policy) } })
                          }}
                          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-normal"
                        >
                          {point.policies.map((p) => (
                            <option key={p.key} value={p.key}>
                              {p.label}
                              {p.key === point.default ? ' (default)' : ''}
                            </option>
                          ))}
                        </select>
                      </label>
                      <p className="mt-1 text-xs text-gray-500">{selected?.description || point.description}</p>
                      {selected && selected.params.length > 0 && (
                        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                          {selected.params.map((param) => (
                            <ParamInput
                              key={param.name}
                              param={param}
                              value={choice.params[param.name]}
                              onChange={(v) =>
                                setPolicies({
                                  ...policies,
                                  [point.key]: { ...choice, params: { ...choice.params, [param.name]: v } },
                                })
                              }
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </section>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving}
                className="flex-1 rounded-lg bg-purple-600 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button type="button" onClick={onClose} className="flex-1 rounded-lg border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Close
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
