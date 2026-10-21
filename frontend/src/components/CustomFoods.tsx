import React, { useEffect, useId, useState } from 'react'
import { Apple, Pencil, Plus, Trash2, AlertCircle, Check } from 'lucide-react'
import { api, ApiError, type CustomFoodInput } from '../api/client'
import { EU_ALLERGENS, allergenLabel } from '../utils/allergens'

// Custom foods (D-32): the user types per-100 g values from a label; they are labelled
// "User-entered", approximate, and visible only to their owner. The planner never uses them.

type Draft = {
  name: string
  serving_description: string
  default_serving_g: string
  state: 'raw' | 'cooked' | 'as_sold'
  energy_kcal: string
  protein_g: string
  carbs_g: string
  fat_g: string
  fiber_g: string
  allergens: string[]
}

const EMPTY: Draft = {
  name: '',
  serving_description: '100 g',
  default_serving_g: '',
  state: 'as_sold',
  energy_kcal: '',
  protein_g: '',
  carbs_g: '',
  fat_g: '',
  fiber_g: '',
  allergens: [],
}

const MACROS: { key: 'energy_kcal' | 'protein_g' | 'carbs_g' | 'fat_g' | 'fiber_g'; label: string; max: number }[] = [
  { key: 'energy_kcal', label: 'Energy (kcal)', max: 900 },
  { key: 'protein_g', label: 'Protein (g)', max: 100 },
  { key: 'carbs_g', label: 'Carbs (g)', max: 100 },
  { key: 'fat_g', label: 'Fat (g)', max: 100 },
  { key: 'fiber_g', label: 'Fibre (g, optional)', max: 100 },
]

const nutrient = (food: any, code: string): string =>
  food.nutrients?.find((n: any) => n.nutrient_code === code)?.amount_per_100g ?? ''

const toDraft = (food: any): Draft => ({
  name: food.name,
  serving_description: food.serving_description,
  default_serving_g: food.default_serving_g ?? '',
  state: food.state,
  energy_kcal: String(Number(nutrient(food, 'energy_kcal'))),
  protein_g: String(Number(nutrient(food, 'protein_g'))),
  carbs_g: String(Number(nutrient(food, 'carbs_g'))),
  fat_g: String(Number(nutrient(food, 'fat_g'))),
  fiber_g: nutrient(food, 'fiber_g') === '' ? '' : String(Number(nutrient(food, 'fiber_g'))),
  allergens: food.allergens ?? [],
})

const toPayload = (d: Draft): CustomFoodInput => ({
  name: d.name.trim(),
  serving_description: d.serving_description.trim() || '100 g',
  default_serving_g: d.default_serving_g.trim() || null,
  state: d.state,
  nutrients: {
    energy_kcal: d.energy_kcal,
    protein_g: d.protein_g,
    carbs_g: d.carbs_g,
    fat_g: d.fat_g,
    ...(d.fiber_g.trim() ? { fiber_g: d.fiber_g } : {}),
  },
  allergens: d.allergens,
})

const errorText = (err: unknown): string => {
  if (err instanceof ApiError) {
    if (err.status === 409 && err.code === 'HTTP_409') {
      return 'You already have a food with that name, or it has been logged and cannot be deleted.'
    }
    if (err.status === 422) return 'Check the values: each is per 100 g, and protein + carbs + fat cannot exceed 100 g.'
    return err.message
  }
  return 'Something went wrong. Please try again.'
}

export default function CustomFoods() {
  const formId = useId()
  const [foods, setFoods] = useState<any[]>([])
  const [draft, setDraft] = useState<Draft>(EMPTY)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  const load = async () => {
    try {
      setFoods(await api.listMyFoods())
    } catch (err) {
      setMessage({ kind: 'error', text: errorText(err) })
    }
  }

  useEffect(() => {
    load()
  }, [])

  const macroGrams = ['protein_g', 'carbs_g', 'fat_g'].reduce((sum, k) => sum + (Number(draft[k as keyof Draft]) || 0), 0)
  const atwater = 4 * (Number(draft.protein_g) || 0) + 4 * (Number(draft.carbs_g) || 0) + 9 * (Number(draft.fat_g) || 0)
  const kcal = Number(draft.energy_kcal) || 0
  // Same tolerance the catalogue uses (AC-50); a hint only, since labels round their values
  const energyLooksOff = draft.energy_kcal !== '' && Math.abs(kcal - atwater) > Math.max(20, 0.15 * kcal)

  const set = (field: keyof Draft, value: string) => setDraft({ ...draft, [field]: value })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setMessage(null)
    try {
      if (editingId) {
        await api.updateCustomFood(editingId, toPayload(draft))
        setMessage({ kind: 'ok', text: `Updated ${draft.name.trim()}. Earlier logs keep the values they were logged with.` })
      } else {
        await api.createCustomFood(toPayload(draft))
        setMessage({ kind: 'ok', text: `Added ${draft.name.trim()}. You can now log it from the dashboard.` })
      }
      setDraft(EMPTY)
      setEditingId(null)
      await load()
    } catch (err) {
      setMessage({ kind: 'error', text: errorText(err) })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (food: any) => {
    if (!window.confirm(`Delete ${food.name}?`)) return
    try {
      await api.deleteCustomFood(food.id)
      if (editingId === food.id) {
        setEditingId(null)
        setDraft(EMPTY)
      }
      await load()
    } catch (err) {
      setMessage({
        kind: 'error',
        text: err instanceof ApiError && err.status === 409 ? `${food.name} is in your logs, so it cannot be deleted.` : errorText(err),
      })
    }
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '0.8125rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    marginBottom: '0.375rem',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {message && (
        <div
          role={message.kind === 'ok' ? 'status' : 'alert'}
          style={{
            background: message.kind === 'ok' ? 'var(--accent-emerald-bg)' : 'var(--accent-rose-bg)',
            border: `1px solid ${message.kind === 'ok' ? 'var(--accent-emerald-border)' : 'var(--accent-rose-border)'}`,
            color: message.kind === 'ok' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {message.kind === 'ok' ? <Check size={18} /> : <AlertCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      <form className="card" onSubmit={handleSubmit}>
        <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '0.35rem' }}>
          {editingId ? 'Edit Food' : 'Add a Food'}
        </h2>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Enter values <strong>per 100 g</strong>, e.g. from the packet label. Your foods are marked “User-entered” and
          approximate, only you can see them, and meal plans keep using reviewed recipes.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
          <div>
            <label htmlFor={`${formId}-name`} style={labelStyle}>Name</label>
            <input id={`${formId}-name`} className="input" value={draft.name} maxLength={200} required
              onChange={(e) => set('name', e.target.value)} placeholder="e.g. Homemade poha" style={{ width: '100%' }} />
          </div>
          <div>
            <label htmlFor={`${formId}-serving`} style={labelStyle}>Serving description</label>
            <input id={`${formId}-serving`} className="input" value={draft.serving_description} maxLength={100}
              onChange={(e) => set('serving_description', e.target.value)} placeholder="1 plate" style={{ width: '100%' }} />
          </div>
          <div>
            <label htmlFor={`${formId}-serving-g`} style={labelStyle}>Grams per serving (optional)</label>
            <input id={`${formId}-serving-g`} className="input" type="number" min="0.01" max="2000" step="any"
              value={draft.default_serving_g} onChange={(e) => set('default_serving_g', e.target.value)} style={{ width: '100%' }} />
          </div>
          <div>
            <label htmlFor={`${formId}-state`} style={labelStyle}>State</label>
            <select id={`${formId}-state`} className="input" value={draft.state}
              onChange={(e) => set('state', e.target.value)} style={{ width: '100%' }}>
              <option value="as_sold">As sold</option>
              <option value="raw">Raw</option>
              <option value="cooked">Cooked</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '0.5rem' }}>
          {MACROS.map(({ key, label, max }) => (
            <div key={key}>
              <label htmlFor={`${formId}-${key}`} style={labelStyle}>{label}</label>
              <input id={`${formId}-${key}`} className="input" type="number" min="0" max={max} step="any"
                required={key !== 'fiber_g'} value={draft[key]} onChange={(e) => set(key, e.target.value)} style={{ width: '100%' }} />
            </div>
          ))}
        </div>
        {macroGrams > 100 && (
          <p role="alert" style={{ fontSize: '0.8125rem', color: 'var(--accent-rose)', marginBottom: '0.5rem' }}>
            Protein + carbs + fat add up to {macroGrams.toFixed(1)} g, more than 100 g per 100 g.
          </p>
        )}
        {energyLooksOff && macroGrams <= 100 && (
          <p style={{ fontSize: '0.8125rem', color: 'var(--accent-amber)', marginBottom: '0.5rem' }}>
            Check the energy: these macros suggest about {Math.round(atwater)} kcal per 100 g.
          </p>
        )}

        <fieldset style={{ border: 'none', padding: 0, margin: '0.75rem 0 1rem' }}>
          <legend style={labelStyle}>Allergens it contains</legend>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {EU_ALLERGENS.map((code) => {
              const checked = draft.allergens.includes(code)
              return (
                <label key={code} className={`badge ${checked ? 'badge-rose' : ''}`}
                  style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', textTransform: 'capitalize' }}>
                  <input type="checkbox" checked={checked}
                    onChange={(e) => setDraft({
                      ...draft,
                      allergens: e.target.checked ? [...draft.allergens, code] : draft.allergens.filter((a) => a !== code),
                    })} />
                  {allergenLabel(code)}
                </label>
              )
            })}
          </div>
        </fieldset>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="submit" className="btn btn-primary" disabled={isSaving || macroGrams > 100}>
            {editingId ? <Pencil size={16} /> : <Plus size={16} />}
            <span>{isSaving ? 'Saving...' : editingId ? 'Save Changes' : 'Add Food'}</span>
          </button>
          {editingId && (
            <button type="button" className="btn btn-ghost" onClick={() => { setEditingId(null); setDraft(EMPTY) }}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="card">
        <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '1rem' }}>My Foods ({foods.length})</h2>
        {foods.length === 0 ? (
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            <Apple size={14} style={{ verticalAlign: 'middle' }} /> No custom foods yet.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.5rem' }}>Food</th>
                  <th style={{ padding: '0.5rem' }}>kcal</th>
                  <th style={{ padding: '0.5rem' }}>P / C / F (g)</th>
                  <th style={{ padding: '0.5rem' }}>Allergens</th>
                  <th style={{ padding: '0.5rem' }}><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {foods.map((f) => (
                  <tr key={f.id} style={{ borderTop: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '0.5rem' }}>
                      <div style={{ color: 'var(--text-main)', fontWeight: 600 }}>{f.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>per 100 g · {f.serving_description}</div>
                    </td>
                    <td style={{ padding: '0.5rem' }}>{Number(nutrient(f, 'energy_kcal'))}</td>
                    <td style={{ padding: '0.5rem', whiteSpace: 'nowrap' }}>
                      {Number(nutrient(f, 'protein_g'))} / {Number(nutrient(f, 'carbs_g'))} / {Number(nutrient(f, 'fat_g'))}
                    </td>
                    <td style={{ padding: '0.5rem', textTransform: 'capitalize' }}>
                      {f.allergens.length ? f.allergens.map(allergenLabel).join(', ') : '—'}
                    </td>
                    <td style={{ padding: '0.5rem', whiteSpace: 'nowrap', textAlign: 'right' }}>
                      <button type="button" className="btn btn-xs btn-ghost" aria-label={`Edit ${f.name}`}
                        onClick={() => { setEditingId(f.id); setDraft(toDraft(f)); setMessage(null) }}>
                        <Pencil size={14} />
                      </button>
                      <button type="button" className="btn btn-xs btn-danger" aria-label={`Delete ${f.name}`}
                        onClick={() => handleDelete(f)}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
