import React, { useState, useEffect, useCallback } from 'react'
import { Activity, Search, Plus, Filter, AlertCircle, Check } from 'lucide-react'
import { api, ApiError } from '../api/client'
import type { Exercise } from '../types'

const MUSCLE_GROUPS = [
  'All',
  'chest',
  'back',
  'shoulders',
  'quadriceps',
  'hamstrings',
  'glutes',
  'biceps',
  'triceps',
  'core',
  'calves',
]

const EQUIPMENT_TYPES = [
  'All',
  'barbell',
  'dumbbell',
  'cable',
  'machine',
  'bodyweight',
  'smith_machine',
]

export const ExercisesCatalogue: React.FC = () => {
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Filters (AC-29)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedMuscle, setSelectedMuscle] = useState('All')
  const [selectedEquipment, setSelectedEquipment] = useState('All')

  // Create Custom Exercise Modal (AC-30)
  const [isCreating, setIsCreating] = useState(false)
  const [customName, setCustomName] = useState('')
  const [customMuscle, setCustomMuscle] = useState('chest')
  const [customEquipment, setCustomEquipment] = useState('dumbbell')
  const [customInstructions, setCustomInstructions] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [createSuccess, setCreateSuccess] = useState<string | null>(null)

  const loadExercises = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const list = await api.getExercises({
        q: searchQuery.trim() || undefined,
        muscle: selectedMuscle !== 'All' ? selectedMuscle : undefined,
        equipment: selectedEquipment !== 'All' ? selectedEquipment : undefined,
      })
      setExercises(list)
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not load exercise catalogue.')
    } finally {
      setIsLoading(false)
    }
  }, [searchQuery, selectedMuscle, selectedEquipment])

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      loadExercises()
    }, 200)
    return () => clearTimeout(debounceTimer)
  }, [loadExercises])

  const handleCreateCustom = async () => {
    setCreateError(null)
    setCreateSuccess(null)

    if (!customName.trim()) {
      setCreateError('Please enter an exercise name.')
      return
    }

    try {
      const created = await api.createExercise({
        name: customName.trim(),
        primary_muscle: customMuscle,
        equipment: customEquipment,
        instructions: customInstructions.trim() || undefined,
      })

      setCreateSuccess(`Custom exercise "${created.name}" created!`)
      setExercises((prev) => [created, ...prev])
      setTimeout(() => {
        setIsCreating(false)
        setCustomName('')
        setCustomInstructions('')
        setCreateSuccess(null)
      }, 1000)
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setCreateError('You already have an exercise with this name.')
      } else {
        setCreateError(err.message || 'Failed to create custom exercise.')
      }
    }
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Activity style={{ color: 'var(--accent-primary)' }} />
            Exercise Catalogue
          </h1>
          <p style={{ marginTop: '0.25rem' }}>Reviewed exercises and custom movement library</p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setIsCreating(true)}
        >
          <Plus size={18} />
          <span>New Custom Exercise</span>
        </button>
      </div>

      {/* Search & Filter Controls (AC-29) */}
      <div className="card" style={{ marginBottom: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ position: 'relative' }}>
          <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input
            type="text"
            className="form-input"
            style={{ paddingLeft: '2.5rem' }}
            placeholder="Search exercises by name (e.g. Squat, Bench Press)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ flex: '1 1 200px' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <Filter size={14} /> Muscle Group
            </label>
            <select
              className="form-select"
              value={selectedMuscle}
              onChange={(e) => setSelectedMuscle(e.target.value)}
            >
              {MUSCLE_GROUPS.map((m) => (
                <option key={m} value={m}>{m.toUpperCase()}</option>
              ))}
            </select>
          </div>

          <div style={{ flex: '1 1 200px' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <Filter size={14} /> Equipment
            </label>
            <select
              className="form-select"
              value={selectedEquipment}
              onChange={(e) => setSelectedEquipment(e.target.value)}
            >
              {EQUIPMENT_TYPES.map((eq) => (
                <option key={eq} value={eq}>{eq.replace('_', ' ').toUpperCase()}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Exercise Grid / List */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="card skeleton" style={{ height: '75px' }} />
          ))}
        </div>
      ) : exercises.length === 0 ? (
        <div className="empty-state">
          <Activity size={40} style={{ color: 'var(--accent-primary)', opacity: 0.8 }} />
          <h3>No matching exercises found</h3>
          <p>Try modifying your search query or filters, or create a new custom exercise.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {exercises.map((ex) => (
            <div
              key={ex.id}
              className="card"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem 1.25rem',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <h2 style={{ fontSize: '1.05rem', color: '#fff' }}>{ex.name}</h2>
                  {ex.is_custom && (
                    <span className="badge badge-amber" style={{ fontSize: '0.6875rem' }}>
                      Custom
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                  Primary: <strong style={{ color: 'var(--text-muted)' }}>{ex.primary_muscle}</strong> • Equipment: <strong style={{ color: 'var(--text-muted)' }}>{ex.equipment}</strong>
                </div>
                {ex.instructions && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem', maxWidth: '650px' }}>
                    {ex.instructions}
                  </p>
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.375rem' }}>
                <span className="badge badge-blue">
                  {ex.primary_muscle}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Custom Exercise Modal (AC-30) */}
      {isCreating && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '1rem' }}>
          <div className="card" style={{ width: '100%', maxWidth: '500px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2>New Custom Exercise</h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setIsCreating(false)}
              >
                ✕
              </button>
            </div>

            {createError && (
              <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
                <AlertCircle size={16} />
                <span>{createError}</span>
              </div>
            )}

            {createSuccess && (
              <div style={{ background: 'var(--accent-emerald-bg)', border: '1px solid var(--accent-emerald-border)', color: 'var(--accent-emerald)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="status">
                <Check size={16} />
                <span>{createSuccess}</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label" htmlFor="custom-name">Exercise Name *</label>
              <input
                id="custom-name"
                type="text"
                className="form-input"
                placeholder="e.g. Incline Neutral Dumbbell Press"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="custom-muscle">Primary Muscle *</label>
              <select
                id="custom-muscle"
                className="form-select"
                value={customMuscle}
                onChange={(e) => setCustomMuscle(e.target.value)}
              >
                {MUSCLE_GROUPS.filter((m) => m !== 'All').map((m) => (
                  <option key={m} value={m}>{m.toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="custom-eq">Equipment *</label>
              <select
                id="custom-eq"
                className="form-select"
                value={customEquipment}
                onChange={(e) => setCustomEquipment(e.target.value)}
              >
                {EQUIPMENT_TYPES.filter((e) => e !== 'All').map((e) => (
                  <option key={e} value={e}>{e.replace('_', ' ').toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="custom-instr">Instructions / Notes (Optional)</label>
              <textarea
                id="custom-instr"
                className="form-textarea"
                rows={3}
                placeholder="Describe setup, grip, cue points..."
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
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
                onClick={handleCreateCustom}
              >
                Save Exercise
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
