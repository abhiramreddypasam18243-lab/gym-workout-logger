import React, { useState, useEffect, useCallback } from 'react'
import { Calendar, Trash2, Dumbbell, AlertCircle, RefreshCw, Activity, Layers } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { WorkoutSession } from '../types'

export const WorkoutHistory: React.FC = () => {
  const { units } = useAuth()
  const isLb = units === 'lb'

  const [workouts, setWorkouts] = useState<WorkoutSession[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadInitial = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const res = await api.getWorkouts(undefined, 10)
      setWorkouts(res.items)
      setNextCursor(res.next_cursor)
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not load workout history.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadInitial()
  }, [loadInitial])

  const loadMore = async () => {
    if (!nextCursor || isLoadingMore) return
    setIsLoadingMore(true)
    try {
      const res = await api.getWorkouts(nextCursor, 10)
      setWorkouts((prev) => [...prev, ...res.items])
      setNextCursor(res.next_cursor)
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not load older workouts.')
    } finally {
      setIsLoadingMore(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this workout session?')) return
    setDeletingId(id)
    try {
      await api.deleteWorkout(id)
      setWorkouts((prev) => prev.filter((w) => w.id !== id))
    } catch (err: any) {
      alert(`Could not delete workout: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  // Calculate volume for working sets in active units (AC-40, AC-96)
  const calculateSessionVolume = (session: WorkoutSession) => {
    let totalKg = 0
    for (const we of session.exercises) {
      for (const s of we.sets) {
        if (!s.is_warmup) {
          totalKg += Number(s.load_kg) * Number(s.reps)
        }
      }
    }
    if (isLb) {
      const lb = totalKg * 2.2046226218
      return `${lb.toLocaleString(undefined, { maximumFractionDigits: 1 })} lb`
    }
    return `${totalKg.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg`
  }

  const formatLoad = (loadKg: number) => {
    if (isLb) {
      const lb = Number(loadKg) * 2.2046226218
      return `${lb.toFixed(1)} lb`
    }
    return `${Number(loadKg).toFixed(1)} kg`
  }

  const countTotalSets = (session: WorkoutSession) => {
    return session.exercises.reduce((acc, e) => acc + e.sets.length, 0)
  }

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--accent-primary-soft)',
            border: '1px solid color-mix(in srgb, var(--accent-primary) 30%, transparent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'none',
          }}>
            <Calendar style={{ color: 'var(--accent-primary)' }} size={20} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.65rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
              Training History
            </h1>
            <p style={{ marginTop: '0.15rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              Detailed ledger of past training sessions, working volume & set telemetry
            </p>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadInitial}
          disabled={isLoading}
          aria-label="Refresh history"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}
        >
          <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {errorMessage && (
        <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Loading Skeletons (AC-90) */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {[1, 2, 3].map((n) => (
            <div key={n} className="card skeleton" style={{ height: '180px' }} />
          ))}
        </div>
      ) : workouts.length === 0 ? (
        /* Empty State (AC-90) */
        <div className="empty-state" style={{ padding: '3.5rem 1.5rem' }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)',
            border: '1px solid color-mix(in srgb, var(--accent-primary) 25%, transparent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.25rem auto',
          }}>
            <Dumbbell size={32} style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>No workout sessions recorded yet</h3>
          <p style={{ maxWidth: '440px', margin: '0 auto' }}>
            Complete a workout in the Workout Logger to generate detailed session archives and volume telemetry here.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {workouts.map((session) => {
            const date = new Date(session.started_at)
            const dateStr = date.toLocaleDateString(undefined, {
              weekday: 'short',
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })
            const timeStr = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
            const totalSets = countTotalSets(session)
            const totalVolume = calculateSessionVolume(session)

            return (
              <div key={session.id} className="card card-glow-cyan" style={{ padding: '1.5rem' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '1rem',
                  marginBottom: '1.25rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  paddingBottom: '1rem',
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <h2 style={{ fontSize: '1.25rem', color: 'var(--text-main)', fontWeight: 800, margin: 0 }}>
                        {dateStr}
                      </h2>
                      <span className="badge badge-blue" style={{ fontSize: '0.6875rem' }}>
                        {timeStr}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Layers size={13} style={{ color: 'var(--accent-primary)' }} />
                        {session.exercises.length} Exercises
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Activity size={13} style={{ color: 'var(--accent-emerald)' }} />
                        {totalSets} Total Sets
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                    <div style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-card)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.5rem 0.85rem',
                      textAlign: 'right',
                    }}>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Total Load Volume
                      </span>
                      <strong style={{
                        color: 'var(--accent-primary)',
                        fontSize: '1.15rem',
                        fontFamily: 'var(--font-display)',
                        fontWeight: 900,
                      }}>
                        {totalVolume}
                      </strong>
                    </div>

                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDelete(session.id)}
                      disabled={deletingId === session.id}
                      title="Delete session"
                      aria-label="Delete workout session"
                      style={{ color: 'var(--accent-rose)', padding: '0.5rem' }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {session.notes && (
                  <div style={{
                    fontSize: '0.8125rem',
                    fontStyle: 'italic',
                    marginBottom: '1rem',
                    color: 'var(--text-muted)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderLeft: '3px solid var(--accent-primary)',
                    padding: '0.5rem 0.85rem',
                    borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                  }}>
                    "{session.notes}"
                  </div>
                )}

                {/* Exercises list in this session */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                  {session.exercises.map((we) => (
                    <div
                      key={we.id}
                      style={{
                        background: 'var(--bg-surface)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '0.85rem 1rem',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '0.65rem',
                      }}>
                        <span style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.925rem' }}>
                          {we.exercise_name || we.exercise?.name || 'Exercise'}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          {we.sets.length} {we.sets.length === 1 ? 'set' : 'sets'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {we.sets.map((s) => (
                          <div
                            key={s.id}
                            style={{
                              background: s.is_warmup ? 'rgba(255,255,255,0.03)' : 'var(--bg-surface)',
                              border: s.is_warmup ? '1px dashed var(--border-subtle)' : '1px solid color-mix(in srgb, var(--accent-primary) 25%, transparent)',
                              borderRadius: 'var(--radius-sm)',
                              padding: '0.4rem 0.65rem',
                              fontSize: '0.8125rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.45rem',
                              fontFamily: 'var(--font-display)',
                            }}
                          >
                            <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>#{s.set_number}</span>
                            <strong style={{ color: s.is_warmup ? 'var(--text-dim)' : 'var(--text-main)' }}>
                              {formatLoad(s.load_kg)} × {s.reps}
                            </strong>
                            {s.rpe && (
                              <span className="badge badge-amber" style={{ fontSize: '0.625rem', padding: '0.1rem 0.35rem' }}>
                                @{s.rpe}
                              </span>
                            )}
                            {s.is_warmup && (
                              <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
                                warmup
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {/* Pagination: Load More (AC-37) */}
          {nextCursor && (
            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={loadMore}
                disabled={isLoadingMore}
                style={{ minWidth: '180px' }}
              >
                {isLoadingMore ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : null}
                <span>Load Earlier Workouts</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
