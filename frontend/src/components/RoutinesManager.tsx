import React, { useState, useEffect, useCallback } from 'react'
import { ClipboardList, Plus, Copy, Trash2, Play, AlertCircle } from 'lucide-react'
import { api } from '../api/client'
import type { Routine, Exercise } from '../types'

interface RoutinesManagerProps {
  onStartRoutine: (routine: Routine) => void
}

export const RoutinesManager: React.FC<RoutinesManagerProps> = ({ onStartRoutine }) => {
  const [routines, setRoutines] = useState<Routine[]>([])
  const [catalogue, setCatalogue] = useState<Exercise[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Create routine modal state
  const [isCreating, setIsCreating] = useState(false)
  const [newRoutineName, setNewRoutineName] = useState('')
  const [newRoutineDesc, setNewRoutineDesc] = useState('')
  const [routineExercises, setRoutineExercises] = useState<
    { exercise_id: string; name: string; target_sets: number; rep_min: number; rep_max: number }[]
  >([])

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const [rList, exList] = await Promise.all([api.getRoutines(), api.getExercises()])
      setRoutines(rList)
      setCatalogue(exList)
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not load routines.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleDuplicate = async (id: string) => {
    try {
      const dup = await api.duplicateRoutine(id)
      setRoutines((prev) => [dup, ...prev])
    } catch (err: any) {
      alert(`Could not duplicate routine: ${err.message}`)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this routine?')) return
    try {
      await api.deleteRoutine(id)
      setRoutines((prev) => prev.filter((r) => r.id !== id))
    } catch (err: any) {
      alert(`Could not delete routine: ${err.message}`)
    }
  }

  const handleAddExerciseToNewRoutine = (ex: Exercise) => {
    setRoutineExercises((prev) => [
      ...prev,
      {
        exercise_id: ex.id,
        name: ex.name,
        target_sets: 3,
        rep_min: 8,
        rep_max: 12,
      },
    ])
  }

  const handleRemoveExerciseFromNewRoutine = (idx: number) => {
    setRoutineExercises((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSaveNewRoutine = async () => {
    if (!newRoutineName.trim()) {
      alert('Please enter a routine name.')
      return
    }
    if (routineExercises.length === 0) {
      alert('Please add at least one exercise to the routine.')
      return
    }

    // Validate rep_min <= rep_max (AC-35)
    for (const re of routineExercises) {
      if (re.rep_min > re.rep_max) {
        alert(`For ${re.name}, min reps (${re.rep_min}) cannot exceed max reps (${re.rep_max}).`)
        return
      }
      if (re.target_sets <= 0) {
        alert(`Target sets must be greater than 0 for ${re.name}.`)
        return
      }
    }

    try {
      const created = await api.createRoutine({
        name: newRoutineName.trim(),
        description: newRoutineDesc.trim() || undefined,
        exercises: routineExercises.map((re, idx) => ({
          exercise_id: re.exercise_id,
          order_in_routine: idx + 1,
          target_sets: re.target_sets,
          rep_min: re.rep_min,
          rep_max: re.rep_max,
        })),
      })
      setRoutines((prev) => [created, ...prev])
      setIsCreating(false)
      setNewRoutineName('')
      setNewRoutineDesc('')
      setRoutineExercises([])
    } catch (err: any) {
      alert(`Could not create routine: ${err.message}`)
    }
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <ClipboardList style={{ color: 'var(--accent-primary)' }} />
            Workout Routines
          </h1>
          <p style={{ marginTop: '0.25rem' }}>Structured templates with target sets and rep ranges</p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setIsCreating(true)}
        >
          <Plus size={18} />
          <span>New Routine</span>
        </button>
      </div>

      {errorMessage && (
        <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {[1, 2].map((n) => (
            <div key={n} className="card skeleton" style={{ height: '160px' }} />
          ))}
        </div>
      ) : routines.length === 0 ? (
        <div className="empty-state">
          <ClipboardList size={40} style={{ color: 'var(--accent-primary)', opacity: 0.8 }} />
          <h3>No routines created yet</h3>
          <p>Create reusable routine templates (e.g. Upper Body, Leg Day) to jumpstart your workouts with target sets and rep ranges.</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsCreating(true)}
          >
            <Plus size={18} />
            <span>Create First Routine</span>
          </button>
        </div>
      ) : (
        <div className="grid-container">
          {routines.map((routine) => (
            <div key={routine.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <h2 style={{ fontSize: '1.2rem', color: '#fff' }}>{routine.name}</h2>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDuplicate(routine.id)}
                      title="Duplicate routine (AC-35)"
                      aria-label="Duplicate routine"
                      style={{ padding: '0.25rem 0.5rem' }}
                    >
                      <Copy size={15} />
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDelete(routine.id)}
                      title="Delete routine"
                      aria-label="Delete routine"
                      style={{ padding: '0.25rem 0.5rem', color: 'var(--accent-rose)' }}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                {routine.description && (
                  <p style={{ fontSize: '0.8125rem', marginBottom: '1rem', color: 'var(--text-muted)' }}>
                    {routine.description}
                  </p>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem' }}>
                  {routine.exercises.map((re, idx) => (
                    <div
                      key={re.id || idx}
                      style={{
                        background: '#090e1a',
                        padding: '0.5rem 0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.8125rem',
                      }}
                    >
                      <span style={{ color: '#fff', fontWeight: 500 }}>
                        {re.exercise?.name || `Exercise ${idx + 1}`}
                      </span>
                      <span className="badge badge-blue">
                        {re.target_sets} sets × {re.rep_min}-{re.rep_max} reps
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Start Workout from routine button (AC-35) */}
              <button
                type="button"
                className="btn btn-primary"
                style={{ width: '100%' }}
                onClick={() => onStartRoutine(routine)}
              >
                <Play size={16} fill="currentColor" />
                <span>Start Workout</span>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create Routine Modal */}
      {isCreating && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '1rem' }}>
          <div className="card" style={{ width: '100%', maxWidth: '580px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2>Create New Routine</h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setIsCreating(false)}
              >
                ✕
              </button>
            </div>

            <div style={{ overflowY: 'auto', flex: 1, paddingRight: '0.25rem' }}>
              <div className="form-group">
                <label className="form-label" htmlFor="routine-name">Routine Name *</label>
                <input
                  id="routine-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Push Hypertrophy A"
                  value={newRoutineName}
                  onChange={(e) => setNewRoutineName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="routine-desc">Description (Optional)</label>
                <input
                  id="routine-desc"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Chest, shoulders & triceps focus"
                  value={newRoutineDesc}
                  onChange={(e) => setNewRoutineDesc(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label className="form-label">Exercises in Routine</label>
                {routineExercises.length === 0 ? (
                  <div style={{ padding: '1rem', background: '#090e1a', borderRadius: 'var(--radius-md)', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8125rem' }}>
                    Select exercises below to add them to this routine.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                    {routineExercises.map((re, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: '#090e1a',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-md)',
                          padding: '0.625rem 0.875rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.5rem',
                          flexWrap: 'wrap',
                        }}
                      >
                        <strong style={{ color: '#fff', fontSize: '0.875rem' }}>{re.name}</strong>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Sets:</span>
                            <input
                              type="number"
                              className="form-input"
                              style={{ width: '55px', minHeight: '32px', padding: '0.2rem 0.4rem' }}
                              value={re.target_sets}
                              min="1"
                              onChange={(e) => {
                                const val = Number(e.target.value)
                                setRoutineExercises((prev) =>
                                  prev.map((item, i) => (i === idx ? { ...item, target_sets: val } : item))
                                )
                              }}
                            />
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Reps:</span>
                            <input
                              type="number"
                              className="form-input"
                              style={{ width: '50px', minHeight: '32px', padding: '0.2rem 0.4rem' }}
                              value={re.rep_min}
                              min="1"
                              onChange={(e) => {
                                const val = Number(e.target.value)
                                setRoutineExercises((prev) =>
                                  prev.map((item, i) => (i === idx ? { ...item, rep_min: val } : item))
                                )
                              }}
                            />
                            <span>-</span>
                            <input
                              type="number"
                              className="form-input"
                              style={{ width: '50px', minHeight: '32px', padding: '0.2rem 0.4rem' }}
                              value={re.rep_max}
                              min="1"
                              onChange={(e) => {
                                const val = Number(e.target.value)
                                setRoutineExercises((prev) =>
                                  prev.map((item, i) => (i === idx ? { ...item, rep_max: val } : item))
                                )
                              }}
                            />
                          </div>

                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => handleRemoveExerciseFromNewRoutine(idx)}
                            style={{ color: 'var(--accent-rose)', padding: '0.25rem' }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Add exercise dropdown / selector */}
              <div className="form-group">
                <label className="form-label">Add Exercise from Catalogue</label>
                <select
                  className="form-select"
                  defaultValue=""
                  onChange={(e) => {
                    const ex = catalogue.find((item) => item.id === e.target.value)
                    if (ex) {
                      handleAddExerciseToNewRoutine(ex)
                      e.target.value = ''
                    }
                  }}
                >
                  <option value="" disabled>Choose an exercise to add...</option>
                  {catalogue.map((ex) => (
                    <option key={ex.id} value={ex.id}>
                      {ex.name} ({ex.primary_muscle})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsCreating(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveNewRoutine}
              >
                Save Routine
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
