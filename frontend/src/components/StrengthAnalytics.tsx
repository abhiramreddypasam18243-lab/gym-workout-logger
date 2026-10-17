import React, { useState, useEffect, useCallback } from 'react'
import { TrendingUp, Trophy, Calendar, Dumbbell, AlertCircle, Table as TableIcon } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Exercise } from '../types'

export const StrengthAnalytics: React.FC = () => {
  const { units } = useAuth()
  const isLb = units === 'lb'

  const [exercises, setExercises] = useState<Exercise[]>([])
  const [selectedExerciseId, setSelectedExerciseId] = useState<string>('')
  const [windowDays, setWindowDays] = useState<number>(90)

  // Data states
  const [trends, setTrends] = useState<any[]>([])
  const [prs, setPrs] = useState<any[]>([])
  const [consistency, setConsistency] = useState<{ weekly_target: number; weeks: any[] } | null>(null)

  // Loading and view mode
  const [isLoading, setIsLoading] = useState(true)
  const [showDataTable, setShowDataTable] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Load exercises list
  useEffect(() => {
    api.getExercises()
      .then((data) => {
        setExercises(data)
        if (data.length > 0) {
          setSelectedExerciseId(data[0].id)
        }
      })
      .catch((err) => console.warn('Could not load exercises:', err))
  }, [])

  // Load analytics for selected exercise & consistency
  const loadAnalytics = useCallback(async () => {
    if (!selectedExerciseId) return
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const [trendData, prData, consistencyData] = await Promise.all([
        api.getStrengthTrends(selectedExerciseId, windowDays),
        api.getExercisePrs(selectedExerciseId),
        api.getWeeklyConsistency(8),
      ])
      setTrends(trendData)
      setPrs(prData.filter((p) => p.is_pr || p.is_baseline))
      setConsistency(consistencyData)
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not load strength analytics.')
    } finally {
      setIsLoading(false)
    }
  }, [selectedExerciseId, windowDays])

  useEffect(() => {
    loadAnalytics()
  }, [loadAnalytics])

  const selectedExercise = exercises.find((e) => e.id === selectedExerciseId)

  // Find max e1rm for chart scaling
  const maxE1rm = trends.reduce((max, t) => Math.max(max, Number(t.e1rm) || 0), 100)

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <TrendingUp style={{ color: 'var(--accent-primary)' }} />
            Strength Analytics
          </h1>
          <p style={{ marginTop: '0.25rem' }}>Estimated 1RM trends, personal records, and consistency</p>
        </div>

        {/* View toggle (AC-93: Table alternative for accessibility) */}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setShowDataTable(!showDataTable)}
          aria-label={showDataTable ? 'Show Visual Chart' : 'Show Data Table Alternative'}
        >
          <TableIcon size={14} />
          <span>{showDataTable ? 'View Chart' : 'Data Table Alternative'}</span>
        </button>
      </div>

      {errorMessage && (
        <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Selector Controls */}
      <div className="card" style={{ marginBottom: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ flex: '1 1 260px' }}>
          <label className="form-label" htmlFor="exercise-select">Select Movement / Exercise</label>
          <select
            id="exercise-select"
            className="form-select"
            value={selectedExerciseId}
            onChange={(e) => setSelectedExerciseId(e.target.value)}
          >
            {exercises.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name} ({ex.primary_muscle})
              </option>
            ))}
          </select>
        </div>

        <div style={{ flex: '0 1 180px' }}>
          <label className="form-label" htmlFor="window-select">Time Window</label>
          <select
            id="window-select"
            className="form-select"
            value={windowDays}
            onChange={(e) => setWindowDays(Number(e.target.value))}
          >
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
            <option value={180}>Last 6 Months</option>
            <option value={365}>Last 1 Year</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="card skeleton" style={{ height: '240px' }} />
          <div className="card skeleton" style={{ height: '140px' }} />
        </div>
      ) : trends.length === 0 ? (
        <div className="empty-state" style={{ marginBottom: '1.5rem' }}>
          <Dumbbell size={40} style={{ color: 'var(--accent-primary)', opacity: 0.8 }} />
          <h3>No strength data recorded yet for this exercise</h3>
          <p>
            Log workout sessions for <strong>{selectedExercise?.name}</strong> to visualize your estimated 1RM trends and unlock personal record milestones.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Trend Card */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.15rem', color: '#fff' }}>
                  {selectedExercise?.name} — Estimated 1RM Progression
                </h2>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Epley Formula: load × (1 + reps/30). Excludes warm-ups (AC-39).
                </span>
              </div>
              <span className="badge badge-blue">
                Current Best: {trends[trends.length - 1]?.e1rm} {isLb ? 'lb' : 'kg'} (Estimated)
              </span>
            </div>

            {/* Visual Chart or Data Table (AC-93) */}
            {showDataTable ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '320px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                      <th style={{ padding: '0.5rem' }}>Date</th>
                      <th style={{ padding: '0.5rem' }}>Best Set (Load × Reps)</th>
                      <th style={{ padding: '0.5rem' }}>Estimated 1RM</th>
                      <th style={{ padding: '0.5rem' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.map((t, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                        <td style={{ padding: '0.5rem', color: '#fff' }}>{t.date}</td>
                        <td style={{ padding: '0.5rem' }}>{t.load} {t.unit} × {t.reps}</td>
                        <td style={{ padding: '0.5rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
                          {t.e1rm} {t.unit}
                        </td>
                        <td style={{ padding: '0.5rem' }}>
                          <span className="badge badge-blue" style={{ fontSize: '0.6875rem' }}>Estimated</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '1rem 0' }}>
                {/* Responsive SVG / CSS Bar Progression Graph */}
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.75rem', height: '180px', paddingTop: '1.5rem', borderBottom: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
                  {trends.map((t, idx) => {
                    const heightPercent = Math.max(20, Math.min(100, (Number(t.e1rm) / maxE1rm) * 100))
                    return (
                      <div
                        key={idx}
                        style={{
                          flex: '1 0 50px',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          height: '100%',
                          justifyContent: 'flex-end',
                        }}
                      >
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.25rem' }}>
                          {t.e1rm}
                        </span>
                        <div
                          style={{
                            width: '100%',
                            maxWidth: '40px',
                            height: `${heightPercent}%`,
                            background: 'linear-gradient(180deg, #38bdf8, #0284c7)',
                            borderRadius: '4px 4px 0 0',
                            boxShadow: '0 0 10px rgba(56,189,248,0.25)',
                            transition: 'height 0.3s ease',
                          }}
                        />
                        <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '0.35rem', whiteSpace: 'nowrap' }}>
                          {t.date.slice(5)}
                        </span>
                      </div>
                    )
                  })}
                </div>
                <div style={{ textAlign: 'right', marginTop: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Values in {isLb ? 'pounds (lb)' : 'kilograms (kg)'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Personal Record Milestones (AC-41) */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Trophy size={20} style={{ color: 'var(--accent-amber)' }} />
              <h2 style={{ fontSize: '1.15rem', color: '#fff' }}>Personal Record Milestones (AC-41)</h2>
            </div>

            {prs.length === 0 ? (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.8125rem' }}>No PR milestones recorded yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {prs.map((p, idx) => (
                  <div
                    key={p.set_id || idx}
                    style={{
                      background: p.is_pr ? 'var(--accent-emerald-bg)' : '#090e1a',
                      border: p.is_pr ? '1px solid var(--accent-emerald-border)' : '1px solid var(--border-subtle)',
                      padding: '0.75rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.5rem',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className={`badge ${p.is_pr ? 'badge-emerald' : 'badge-blue'}`}>
                          {p.is_pr ? 'New PR' : 'Baseline Benchmark'}
                        </span>
                        <strong style={{ color: '#fff' }}>
                          {p.load} {p.unit} × {p.reps} reps
                        </strong>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem', display: 'block' }}>
                        Completed on {p.completed_at ? new Date(p.completed_at).toLocaleDateString() : '—'}
                      </span>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Estimated 1RM</span>
                      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: p.is_pr ? 'var(--accent-emerald)' : 'var(--accent-primary)' }}>
                        {p.e1rm} {p.unit}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Weekly Consistency (AC-44) */}
          {consistency && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Calendar size={20} style={{ color: 'var(--accent-primary)' }} />
                  <h2 style={{ fontSize: '1.15rem', color: '#fff' }}>Weekly Consistency (AC-44)</h2>
                </div>
                <span className="badge badge-blue">
                  Target: {consistency.weekly_target} sessions / week
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '0.75rem' }}>
                {consistency.weeks.map((w, idx) => {
                  const met = w.session_count >= consistency.weekly_target
                  return (
                    <div
                      key={idx}
                      style={{
                        background: '#090e1a',
                        border: met ? '1px solid var(--accent-emerald-border)' : '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        padding: '0.75rem 0.5rem',
                        textAlign: 'center',
                      }}
                    >
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', display: 'block' }}>
                        {w.week_start.slice(5)}
                      </span>
                      <div style={{ fontSize: '1.35rem', fontWeight: 800, color: met ? 'var(--accent-emerald)' : '#fff', margin: '0.25rem 0' }}>
                        {w.session_count}
                      </div>
                      <span style={{ fontSize: '0.6875rem', color: met ? 'var(--accent-emerald)' : 'var(--text-dim)' }}>
                        {met ? 'Met Target' : 'sessions'}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
