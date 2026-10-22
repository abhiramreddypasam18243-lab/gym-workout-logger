import React, { useEffect, useId, useState } from 'react'
import { BarChart3, Pencil, Check, X } from 'lucide-react'
import { api, ApiError } from '../api/client'

// Working sets per muscle this week against the user's own targets (D-34)

const COMMON_MUSCLES = ['chest', 'back', 'shoulders', 'quads', 'hamstrings', 'glutes', 'biceps', 'triceps', 'core']

export const WeeklyVolumeCard: React.FC = () => {
  const formId = useId()
  const [week, setWeek] = useState<{ week_start: string; week_end: string; muscles: any[] } | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const load = async () => {
    try {
      setWeek(await api.getWeeklyVolume())
    } catch {
      setError('Could not load this week’s volume.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  const startEditing = () => {
    const current: Record<string, string> = {}
    for (const m of COMMON_MUSCLES) current[m] = ''
    for (const row of week?.muscles ?? []) {
      current[row.muscle] = row.target ? String(row.target) : current[row.muscle] ?? ''
    }
    setDraft(current)
    setError(null)
    setIsEditing(true)
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    const targets: Record<string, number> = {}
    for (const [muscle, value] of Object.entries(draft)) {
      if (value.trim() !== '') targets[muscle] = Number(value)
    }
    setIsSaving(true)
    try {
      await api.putWeeklyVolumeTargets(targets)
      setIsEditing(false)
      await load()
    } catch (err) {
      setError(err instanceof ApiError && err.status === 422 ? 'Each target must be 1 to 40 sets.' : 'Could not save targets.')
    } finally {
      setIsSaving(false)
    }
  }

  const rows = week?.muscles ?? []

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart3 size={18} style={{ color: 'var(--accent-primary)' }} /> Weekly Sets per Muscle
          </h2>
          {week && (
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              Working sets, {week.week_start} to {week.week_end}. Warm-ups are not counted.
            </p>
          )}
        </div>
        {!isEditing && (
          <button type="button" className="btn btn-sm btn-secondary" onClick={startEditing}>
            <Pencil size={14} />
            <span>Set targets</span>
          </button>
        )}
      </div>

      {error && (
        <p role="alert" style={{ color: 'var(--accent-rose)', fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
          {error}
        </p>
      )}

      {isEditing ? (
        <form onSubmit={save}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.6rem', marginBottom: '0.9rem' }}>
            {Object.keys(draft).map((muscle) => (
              <div key={muscle}>
                <label htmlFor={`${formId}-${muscle}`} style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize', marginBottom: '0.25rem' }}>
                  {muscle}
                </label>
                <input
                  id={`${formId}-${muscle}`}
                  className="input"
                  type="number"
                  min="1"
                  max="40"
                  step="1"
                  placeholder="—"
                  value={draft[muscle]}
                  onChange={(e) => setDraft({ ...draft, [muscle]: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.75rem' }}>
            Sets per week you aim for. Leave a muscle blank for no target.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="submit" className="btn btn-sm btn-primary" disabled={isSaving}>
              <Check size={14} />
              <span>{isSaving ? 'Saving...' : 'Save targets'}</span>
            </button>
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setIsEditing(false)}>
              <X size={14} />
              <span>Cancel</span>
            </button>
          </div>
        </form>
      ) : rows.length === 0 ? (
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          No working sets logged this week yet. Set weekly targets to track volume per muscle group.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {rows.map((row) => {
            const pct = row.target ? Math.min(100, (row.sets / row.target) * 100) : 0
            return (
              <div key={row.muscle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>
                  <span style={{ textTransform: 'capitalize', color: 'var(--text-main)' }}>{row.muscle}</span>
                  <span style={{ color: row.met ? 'var(--accent-emerald)' : 'var(--text-muted)', fontFamily: 'var(--font-display)' }}>
                    {row.sets}
                    {row.target ? ` / ${row.target} sets` : ' sets'}
                    {row.met ? ' ✓' : ''}
                  </span>
                </div>
                {row.target ? (
                  <div
                    role="progressbar"
                    aria-label={`${row.muscle} weekly sets`}
                    aria-valuemin={0}
                    aria-valuemax={row.target}
                    aria-valuenow={row.sets}
                    style={{ height: '6px', background: 'var(--bg-surface-elevated)', borderRadius: '3px', overflow: 'hidden' }}
                  >
                    <div style={{ width: `${pct}%`, height: '100%', background: row.met ? 'var(--accent-emerald)' : 'var(--accent-primary)' }} />
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
