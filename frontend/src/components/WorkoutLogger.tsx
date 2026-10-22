import React, { useState, useEffect } from 'react'
import { Plus, Trash2, Clock, Check, AlertCircle, Dumbbell, Copy, Timer } from 'lucide-react'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { playSetCompleteSound, playMicroClick } from '../utils/audio'
import { MotivationalQuoteCard } from './MotivationalQuoteCard'
import { OverloadHint } from './OverloadHint'
import type { Exercise, Routine } from '../types'

interface ActiveSet {
  set_number: number
  reps: number | string
  load_display: number | string
  rpe?: number | string
  is_warmup: boolean
  completed?: boolean
  notes?: string
}

interface ActiveExercise {
  exercise_id: string
  name: string
  order_in_session: number
  notes?: string
  rep_min?: number
  rep_max?: number
  sets: ActiveSet[]
}

interface WorkoutLoggerProps {
  prefilledRoutine?: Routine | null
  onWorkoutSaved?: () => void
}

export const WorkoutLogger: React.FC<WorkoutLoggerProps> = ({ prefilledRoutine, onWorkoutSaved }) => {
  const { units } = useAuth()
  const isLb = units === 'lb'

  const [routineId, setRoutineId] = useState<string | null>(null)
  const [sessionNotes, setSessionNotes] = useState('')
  const [exercises, setExercises] = useState<ActiveExercise[]>([])
  const [startTime] = useState<Date>(() => new Date())
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  // Exercise catalogue for adding exercises
  const [catalogue, setCatalogue] = useState<Exercise[]>([])
  const [isSearchingExercise, setIsSearchingExercise] = useState(false)
  const [exerciseSearchQuery, setExerciseSearchQuery] = useState('')

  // State management: loading, saving, errors, success (AC-90)
  const [isSaving, setIsSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((new Date().getTime() - startTime.getTime()) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [startTime])

  // Load exercises catalogue
  useEffect(() => {
    api.getExercises()
      .then(setCatalogue)
      .catch((err) => console.warn('Could not load exercise catalogue:', err))
  }, [])

  // Handle prefilled routine (AC-35)
  useEffect(() => {
    if (prefilledRoutine) {
      setRoutineId(prefilledRoutine.id)
      const mapped: ActiveExercise[] = prefilledRoutine.exercises.map((re, idx) => ({
        exercise_id: re.exercise_id,
        name: re.exercise?.name || `Exercise ${idx + 1}`,
        order_in_session: idx + 1,
        notes: re.notes || '',
        rep_min: re.rep_min,
        rep_max: re.rep_max,
        sets: [
          {
            set_number: 1,
            reps: re.rep_min || 8,
            load_display: 0,
            is_warmup: false,
          },
        ],
      }))
      setExercises(mapped)
    }
  }, [prefilledRoutine])

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  // Add exercise to active session
  const addExercise = (exercise: Exercise) => {
    const newEx: ActiveExercise = {
      exercise_id: exercise.id,
      name: exercise.name,
      order_in_session: exercises.length + 1,
      sets: [
        {
          set_number: 1,
          reps: 10,
          load_display: 20,
          is_warmup: false,
        },
      ],
    }
    setExercises([...exercises, newEx])
    setIsSearchingExercise(false)
    setExerciseSearchQuery('')
  }

  // Remove exercise
  const removeExercise = (exerciseIndex: number) => {
    const updated = exercises.filter((_, idx) => idx !== exerciseIndex)
    setExercises(updated.map((ex, idx) => ({ ...ex, order_in_session: idx + 1 })))
  }

  // Fast set entry (AC-95): 1 interaction copies previous set's reps and load
  const addSet = (exerciseIndex: number) => {
    const targetEx = exercises[exerciseIndex]
    const lastSet = targetEx.sets[targetEx.sets.length - 1]

    const newSet: ActiveSet = {
      set_number: targetEx.sets.length + 1,
      reps: lastSet ? lastSet.reps : 10,
      load_display: lastSet ? lastSet.load_display : 20,
      rpe: lastSet ? lastSet.rpe : '',
      is_warmup: false,
    }

    const updated = [...exercises]
    updated[exerciseIndex].sets.push(newSet)
    setExercises(updated)
  }

  const removeSet = (exerciseIndex: number, setIndex: number) => {
    const updated = [...exercises]
    updated[exerciseIndex].sets = updated[exerciseIndex].sets
      .filter((_, idx) => idx !== setIndex)
      .map((s, idx) => ({ ...s, set_number: idx + 1 }))
    setExercises(updated)
  }

  const updateSet = (
    exerciseIndex: number,
    setIndex: number,
    field: keyof ActiveSet,
    value: any
  ) => {
    const updated = [...exercises]
    updated[exerciseIndex].sets[setIndex] = {
      ...updated[exerciseIndex].sets[setIndex],
      [field]: value,
    }
    setExercises(updated)
  }

  const toggleSetComplete = (exerciseIndex: number, setIndex: number) => {
    const isNowComplete = !exercises[exerciseIndex].sets[setIndex].completed
    updateSet(exerciseIndex, setIndex, 'completed', isNowComplete)
    if (isNowComplete) {
      playSetCompleteSound()
      window.dispatchEvent(new CustomEvent('titan-start-timer', { detail: { seconds: 90 } }))
    } else {
      playMicroClick()
    }
  }

  // Calculate live session statistics
  const totalVolume = exercises.reduce((accEx, ex) => {
    return accEx + ex.sets.reduce((accSet, s) => {
      const load = Number(s.load_display) || 0
      const reps = Number(s.reps) || 0
      return accSet + (load * reps)
    }, 0)
  }, 0)

  const totalSetsCount = exercises.reduce((acc, ex) => acc + ex.sets.length, 0)
  const completedSetsCount = exercises.reduce(
    (acc, ex) => acc + ex.sets.filter((s) => s.completed).length,
    0
  )
  const sessionCompletionPct = totalSetsCount > 0 ? Math.round((completedSetsCount / totalSetsCount) * 100) : 0

  // Save Workout
  const handleSaveWorkout = async () => {
    setErrorMessage(null)
    setFieldErrors({})
    setSuccessMessage(null)

    if (exercises.length === 0) {
      setErrorMessage('Please add at least one exercise to your session.')
      return
    }

    // Build payload
    const now = new Date()
    const payloadExercises = []

    for (let eIdx = 0; eIdx < exercises.length; eIdx++) {
      const ex = exercises[eIdx]
      if (ex.sets.length === 0) {
        setErrorMessage(`Exercise "${ex.name}" has no sets recorded.`)
        return
      }

      const sets = []
      for (let sIdx = 0; sIdx < ex.sets.length; sIdx++) {
        const s = ex.sets[sIdx]
        const reps = Number(s.reps)
        const loadDisp = Number(s.load_display)

        // Validate client side before sending
        if (isNaN(reps) || reps <= 0) {
          const fieldKey = `ex_${eIdx}_set_${sIdx}_reps`
          setFieldErrors({ [fieldKey]: 'Reps must be greater than 0' })
          setErrorMessage(`Set ${s.set_number} in ${ex.name} must have reps > 0`)
          return
        }

        if (isNaN(loadDisp) || loadDisp < 0) {
          const fieldKey = `ex_${eIdx}_set_${sIdx}_load`
          setFieldErrors({ [fieldKey]: 'Load must be >= 0' })
          setErrorMessage(`Set ${s.set_number} in ${ex.name} cannot have negative load`)
          return
        }

        // Convert lb to kg if user unit is lb (AC-16)
        const load_kg = isLb ? Number((loadDisp * 0.45359237).toFixed(4)) : loadDisp

        let rpeNum: number | undefined = undefined
        if (s.rpe !== '' && s.rpe !== undefined && s.rpe !== null) {
          rpeNum = Number(s.rpe)
          if (isNaN(rpeNum) || rpeNum < 1.0 || rpeNum > 10.0 || (rpeNum * 2) % 1 !== 0) {
            setErrorMessage(`RPE must be between 1.0 and 10.0 in steps of 0.5`)
            return
          }
        }

        sets.push({
          set_number: s.set_number,
          reps,
          load_kg,
          rpe: rpeNum,
          is_warmup: !!s.is_warmup,
          notes: s.notes || null,
          completed_at: now.toISOString(),
        })
      }

      payloadExercises.push({
        exercise_id: ex.exercise_id,
        order_in_session: ex.order_in_session,
        notes: ex.notes || null,
        sets,
      })
    }

    setIsSaving(true)
    try {
      await api.createWorkout({
        routine_id: routineId,
        started_at: startTime.toISOString(),
        completed_at: now.toISOString(),
        notes: sessionNotes || null,
        exercises: payloadExercises,
      })

      setSuccessMessage('Workout recorded successfully!')
      setExercises([])
      setSessionNotes('')
      setRoutineId(null)
      if (onWorkoutSaved) {
        onWorkoutSaved()
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message || 'Validation error while saving workout.')
      } else {
        setErrorMessage('Failed to save workout session. Please check your network connection.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  const filteredCatalogue = catalogue.filter((item) =>
    item.name.toLowerCase().includes(exerciseSearchQuery.toLowerCase())
  )

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Morale Boost Strip */}
      <div style={{ marginBottom: '1.25rem' }}>
        <MotivationalQuoteCard variant="strip" />
      </div>

      {/* Session Header Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
              <Dumbbell style={{ color: 'var(--accent-primary)' }} />
              Active Gym Session
            </h1>
            <p style={{ marginTop: '0.25rem' }}>
              {startTime.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', background: 'var(--bg-surface)', padding: '0.5rem 0.875rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <Clock size={16} style={{ color: 'var(--accent-primary)' }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1rem', color: 'var(--text-main)' }}>
                {formatTime(elapsedSeconds)}
              </span>
            </div>

            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSaveWorkout}
              disabled={isSaving || exercises.length === 0}
            >
              {isSaving ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : <Check size={18} />}
              <span>Finish & Save</span>
            </button>
          </div>
        </div>

        {/* Status Banners (AC-90) */}
        {errorMessage && (
          <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div style={{ background: 'var(--accent-emerald-bg)', border: '1px solid var(--accent-emerald-border)', color: 'var(--accent-emerald)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="status">
            <Check size={18} />
            <span>{successMessage}</span>
          </div>
        )}

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="session-notes">Session Notes (Optional)</label>
          <input
            id="session-notes"
            type="text"
            className="form-input"
            placeholder="e.g. Felt energetic, increased bench load"
            value={sessionNotes}
            onChange={(e) => setSessionNotes(e.target.value)}
          />
        </div>

        {/* Live Session Telemetry HUD */}
        {exercises.length > 0 && (
          <div
            style={{
              marginTop: '1.25rem',
              padding: '1rem',
              background: 'var(--bg-surface)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid color-mix(in srgb, var(--accent-primary) 20%, transparent)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-live">
                  <span className="pulse-dot" /> LIVE TRACKING
                </span>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  {exercises.length} {exercises.length === 1 ? 'Movement' : 'Movements'} in rotation
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                <div style={{ fontSize: '0.875rem' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Volume: </span>
                  <span className="mono-stat" style={{ color: 'var(--accent-primary)', fontSize: '1rem' }}>
                    {totalVolume.toLocaleString()} {isLb ? 'lb' : 'kg'}
                  </span>
                </div>

                <div style={{ fontSize: '0.875rem' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Sets: </span>
                  <span className="mono-stat" style={{ color: 'var(--accent-emerald)', fontSize: '1rem' }}>
                    {completedSetsCount}/{totalSetsCount} ({sessionCompletionPct}%)
                  </span>
                </div>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => window.dispatchEvent(new CustomEvent('titan-start-timer', { detail: { seconds: 90 } }))}
                  style={{ padding: '0.2rem 0.5rem', height: '28px', fontSize: '0.75rem' }}
                  title="Trigger 90s rest timer"
                >
                  <Timer size={13} style={{ color: 'var(--accent-primary)' }} />
                  <span>Rest 90s</span>
                </button>
              </div>
            </div>

            {/* Session set completion progress bar */}
            <div style={{ width: '100%', height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '2px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${sessionCompletionPct}%`,
                  height: '100%',
                  background: 'var(--accent-primary)',
                  borderRadius: '2px',
                  transition: 'width 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Exercises in Session */}
      {exercises.length === 0 ? (
        <div className="empty-state" style={{ marginBottom: '1.5rem' }}>
          <Dumbbell size={40} style={{ color: 'var(--accent-primary)', opacity: 0.8 }} />
          <h3>No exercises added yet</h3>
          <p>Begin your workout by searching and adding an exercise from the catalogue.</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsSearchingExercise(true)}
          >
            <Plus size={18} />
            <span>Add First Exercise</span>
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.5rem' }}>
          {exercises.map((ex, exIdx) => (
            <div key={`${ex.exercise_id}-${exIdx}`} className="card" style={{ borderLeft: '4px solid var(--accent-primary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.875rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="badge badge-blue">#{ex.order_in_session}</span>
                  <h2 style={{ fontSize: '1.15rem' }}>{ex.name}</h2>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => removeExercise(exIdx)}
                  title="Remove exercise"
                  aria-label={`Remove ${ex.name}`}
                  style={{ color: 'var(--accent-rose)' }}
                >
                  <Trash2 size={16} />
                </button>
              </div>

              <OverloadHint
                exerciseId={ex.exercise_id}
                repMin={ex.rep_min}
                repMax={ex.rep_max}
                onUseLoad={(load) => {
                  const updated = [...exercises]
                  updated[exIdx] = {
                    ...updated[exIdx],
                    sets: updated[exIdx].sets.map((st) => (st.is_warmup ? st : { ...st, load_display: load })),
                  }
                  setExercises(updated)
                }}
              />

              {/* Set Table */}
              <div style={{ overflowX: 'auto', marginBottom: '0.75rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '340px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                      <th style={{ padding: '0.5rem' }}>Set</th>
                      <th style={{ padding: '0.5rem' }}>{isLb ? 'Load (lb)' : 'Load (kg)'}</th>
                      <th style={{ padding: '0.5rem' }}>Reps</th>
                      <th style={{ padding: '0.5rem' }}>RPE</th>
                      <th style={{ padding: '0.5rem', textAlign: 'center' }}>Warm-up</th>
                      <th style={{ padding: '0.5rem', textAlign: 'center' }}>Done</th>
                      <th style={{ padding: '0.5rem', textAlign: 'right' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ex.sets.map((s, sIdx) => {
                      const loadErrKey = `ex_${exIdx}_set_${sIdx}_load`
                      const repsErrKey = `ex_${exIdx}_set_${sIdx}_reps`
                      const loadNum = Number(s.load_display) || 0
                      const repsNum = Number(s.reps) || 0
                      const e1rm = loadNum > 0 && repsNum > 0 ? (repsNum === 1 ? loadNum : Math.round(loadNum * (1 + repsNum / 30) * 10) / 10) : null

                      return (
                        <tr
                          key={sIdx}
                          className={s.completed ? 'set-row-completed' : ''}
                          style={{
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                            background: s.completed ? 'color-mix(in srgb, var(--accent-emerald) 8%, transparent)' : 'transparent',
                            transition: 'background 0.25s ease',
                          }}
                        >
                          <td style={{ padding: '0.5rem', fontWeight: 700 }}>
                            <span style={{ color: s.completed ? 'var(--accent-emerald)' : 'var(--text-main)' }}>
                              {s.set_number}
                            </span>
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <input
                                type="number"
                                className="form-input"
                                style={{ width: '85px', minHeight: '36px', padding: '0.35rem 0.5rem', fontFamily: 'var(--font-mono)' }}
                                value={s.load_display}
                                min="0"
                                step={isLb ? '0.5' : '0.5'}
                                aria-describedby={fieldErrors[loadErrKey] ? loadErrKey : undefined}
                                aria-invalid={!!fieldErrors[loadErrKey]}
                                onChange={(e) => updateSet(exIdx, sIdx, 'load_display', e.target.value)}
                              />
                              {e1rm && !s.is_warmup && (
                                <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                                  e1RM: {e1rm}
                                </span>
                              )}
                            </div>
                            {fieldErrors[loadErrKey] && (
                              <div id={loadErrKey} className="form-error">{fieldErrors[loadErrKey]}</div>
                            )}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            <input
                              type="number"
                              className="form-input"
                              style={{ width: '75px', minHeight: '36px', padding: '0.35rem 0.5rem', fontFamily: 'var(--font-mono)' }}
                              value={s.reps}
                              min="1"
                              step="1"
                              aria-describedby={fieldErrors[repsErrKey] ? repsErrKey : undefined}
                              aria-invalid={!!fieldErrors[repsErrKey]}
                              onChange={(e) => updateSet(exIdx, sIdx, 'reps', e.target.value)}
                            />
                            {fieldErrors[repsErrKey] && (
                              <div id={repsErrKey} className="form-error">{fieldErrors[repsErrKey]}</div>
                            )}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            <select
                              className="form-select"
                              style={{ width: '80px', minHeight: '36px', padding: '0.35rem 0.5rem', fontFamily: 'var(--font-mono)' }}
                              value={s.rpe || ''}
                              onChange={(e) => updateSet(exIdx, sIdx, 'rpe', e.target.value)}
                            >
                              <option value="">-</option>
                              {[6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0].map((r) => (
                                <option key={r} value={r}>{r}</option>
                              ))}
                            </select>
                          </td>

                          <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={s.is_warmup}
                              onChange={(e) => updateSet(exIdx, sIdx, 'is_warmup', e.target.checked)}
                              style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)', cursor: 'pointer' }}
                              aria-label={`Mark set ${s.set_number} as warm-up`}
                            />
                          </td>

                          {/* Interactive Done Checkmark */}
                          <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                            <button
                              type="button"
                              onClick={() => toggleSetComplete(exIdx, sIdx)}
                              style={{
                                width: '30px',
                                height: '30px',
                                borderRadius: 'var(--radius-sm)',
                                border: s.completed ? '1px solid var(--accent-emerald)' : '1px solid rgba(255, 255, 255, 0.15)',
                                background: s.completed ? 'var(--accent-emerald)' : 'rgba(255, 255, 255, 0.05)',
                                color: s.completed ? 'var(--bg-surface)' : 'var(--text-dim)',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                boxShadow: s.completed ? 'none' : 'none',
                              }}
                              title={s.completed ? 'Mark incomplete' : 'Mark set done and start 90s recovery timer'}
                              aria-label={`Toggle set ${s.set_number} completion`}
                            >
                              <Check size={16} strokeWidth={s.completed ? 3 : 2} />
                            </button>
                          </td>

                          <td style={{ padding: '0.5rem', textAlign: 'right' }}>
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              onClick={() => removeSet(exIdx, sIdx)}
                              disabled={ex.sets.length <= 1}
                              title="Delete set"
                              aria-label={`Delete set ${s.set_number}`}
                              style={{ padding: '0.25rem 0.5rem' }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Fast Set Add (AC-95: 1-click adds next set with copied values) */}
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => addSet(exIdx)}
                  title="Adds next set duplicating current load and reps"
                >
                  <Copy size={14} />
                  <span>+ Copy Set (Fast Entry)</span>
                </button>
              </div>
            </div>
          ))}

          {/* Add Another Exercise Button */}
          <div style={{ textAlign: 'center' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsSearchingExercise(true)}
            >
              <Plus size={18} />
              <span>Add Another Exercise</span>
            </button>
          </div>
        </div>
      )}

      {/* Add Exercise Modal / Drawer */}
      {isSearchingExercise && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '1rem' }}>
          <div className="card" style={{ width: '100%', maxWidth: '500px', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2>Select Exercise</h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setIsSearchingExercise(false)}
              >
                ✕
              </button>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <input
                type="text"
                className="form-input"
                placeholder="Search exercise by name..."
                value={exerciseSearchQuery}
                onChange={(e) => setExerciseSearchQuery(e.target.value)}
                autoFocus
              />
            </div>

            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {filteredCatalogue.length === 0 ? (
                <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-dim)' }}>
                  No matching exercises found.
                </div>
              ) : (
                filteredCatalogue.map((ex) => (
                  <button
                    key={ex.id}
                    type="button"
                    className="btn btn-secondary"
                    style={{ justifyContent: 'space-between', textAlign: 'left', padding: '0.75rem 1rem' }}
                    onClick={() => addExercise(ex)}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{ex.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        {ex.primary_muscle} • {ex.equipment}
                      </div>
                    </div>
                    <span className="badge badge-blue">Select</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
