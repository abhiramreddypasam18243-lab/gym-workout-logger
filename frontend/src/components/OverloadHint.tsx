import React, { useEffect, useState } from 'react'
import { TrendingUp, Pause } from 'lucide-react'
import { api } from '../api/client'

// Progressive overload hint (D-33): a rule-based suggestion from the last session, not coaching advice

interface OverloadHintProps {
  exerciseId: string
  repMin?: number
  repMax?: number
  onUseLoad: (load: string) => void
}

export const OverloadHint: React.FC<OverloadHintProps> = ({ exerciseId, repMin, repMax, onUseLoad }) => {
  const [hint, setHint] = useState<any | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .getNextLoad(exerciseId, repMin, repMax)
      .then((h) => {
        if (!cancelled) setHint(h)
      })
      .catch(() => {
        if (!cancelled) setHint(null)
      })
    return () => {
      cancelled = true
    }
  }, [exerciseId, repMin, repMax])

  if (!hint || hint.action === 'no_history') return null

  const increase = hint.action === 'increase_load'
  const load = Number(hint.suggested_load)

  return (
    <div
      role="note"
      title={hint.note}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        flexWrap: 'wrap',
        fontSize: '0.8125rem',
        padding: '0.5rem 0.75rem',
        marginBottom: '0.75rem',
        borderRadius: 'var(--radius-sm)',
        background: increase ? 'var(--accent-emerald-bg)' : 'var(--bg-surface-elevated)',
        border: `1px solid ${increase ? 'var(--accent-emerald-border)' : 'var(--border-subtle)'}`,
        color: 'var(--text-muted)',
      }}
    >
      {increase ? <TrendingUp size={16} style={{ color: 'var(--accent-emerald)' }} /> : <Pause size={16} />}
      <span style={{ flex: '1 1 220px' }}>
        <strong style={{ color: 'var(--text-main)' }}>
          {increase ? `Try ${load} ${hint.unit}` : `Stay at ${load} ${hint.unit}`}
        </strong>{' '}
        — last time ({hint.last_session_date}): {hint.reps_at_top_load.join(', ')} reps at {Number(hint.top_load)} {hint.unit}.{' '}
        {hint.reason}
      </span>
      <button type="button" className="btn btn-xs btn-outline" onClick={() => onUseLoad(String(load))}>
        Use {load} {hint.unit}
      </button>
    </div>
  )
}
