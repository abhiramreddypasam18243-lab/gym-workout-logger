import React, { useState, useEffect, useCallback } from 'react'
import {
  Calendar,
  Sparkles,
  AlertTriangle,
  Info,
  Clock,
  ChefHat,
  ChevronDown,
  ChevronUp,
  Trash2,
  ShieldAlert,
} from 'lucide-react'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface FilterRemoved {
  filter: string
  removed: number
}

interface InfeasibleData {
  status: 'infeasible'
  slot: string
  day: string
  filters: FilterRemoved[]
  relaxable: string[]
  message: string
}

export const MealPlanView: React.FC = () => {
  const { profile } = useAuth()
  const isCaloriesHidden = profile?.calories_hidden || false
  const isNutritionPaused = profile?.nutrition_paused || false
  const isAdultConfirmed = !!profile?.adult_confirmed_at

  const [plans, setPlans] = useState<any[]>([])
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [currentPlan, setCurrentPlan] = useState<any | null>(null)
  const [infeasibleData, setInfeasibleData] = useState<InfeasibleData | null>(null)

  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [showGeneratorModal, setShowGeneratorModal] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Generator form fields
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [daysCount, setDaysCount] = useState(7)
  const [selectedSlots, setSelectedSlots] = useState<string[]>([
    'breakfast',
    'lunch',
    'dinner',
    'snack',
  ])
  const [maxMinutes, setMaxMinutes] = useState<number | string>('')
  const [dailyBudget, setDailyBudget] = useState<number | string>('')

  // Load existing plans
  const loadPlans = useCallback(async () => {
    if (isNutritionPaused || !isAdultConfirmed) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setErrorMsg(null)
    try {
      const planList = await api.listMealPlans()
      setPlans(planList)
      if (planList.length > 0) {
        const fullPlan = await api.getMealPlan(planList[0].id)
        setSelectedPlanId(planList[0].id)
        setCurrentPlan(fullPlan)
      } else {
        setSelectedPlanId(null)
        setCurrentPlan(null)
      }
    } catch (err: any) {
      console.warn('Could not load meal plans:', err)
      setErrorMsg(err.message || 'Failed to load meal plans.')
    } finally {
      setIsLoading(false)
    }
  }, [isNutritionPaused, isAdultConfirmed])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  // Select a different plan
  const handleSelectPlan = async (id: string) => {
    setIsLoading(true)
    setInfeasibleData(null)
    try {
      const fullPlan = await api.getMealPlan(id)
      setSelectedPlanId(id)
      setCurrentPlan(fullPlan)
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not load plan details')
    } finally {
      setIsLoading(false)
    }
  }

  // Delete plan
  const handleDeletePlan = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this meal plan?')) return
    try {
      await api.deleteMealPlan(id)
      await loadPlans()
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not delete meal plan')
    }
  }

  // Handle plan generation
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsGenerating(true)
    setErrorMsg(null)
    setInfeasibleData(null)

    try {
      const payload: any = {
        start_date: startDate,
        days: Number(daysCount),
        meal_slots: selectedSlots,
      }
      if (maxMinutes !== '') {
        payload.max_minutes = Number(maxMinutes)
      }
      if (dailyBudget !== '') {
        payload.daily_budget_minor = Number(dailyBudget) * 100 // convert to minor units
      }

      const res = await api.generateMealPlan(payload)
      if (res.status === 'infeasible') {
        setInfeasibleData(res)
        setShowGeneratorModal(false)
      } else {
        setShowGeneratorModal(false)
        await loadPlans()
        setCurrentPlan(res)
        setSelectedPlanId(res.id)
      }
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 422) {
        setErrorMsg('Please set your nutrition targets first before generating a meal plan.')
      } else {
        setErrorMsg(err.message || 'Generation failed.')
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const toggleSlot = (slot: string) => {
    if (selectedSlots.includes(slot)) {
      if (selectedSlots.length > 1) {
        setSelectedSlots(selectedSlots.filter((s) => s !== slot))
      }
    } else {
      setSelectedSlots([...selectedSlots, slot])
    }
  }

  if (isNutritionPaused) {
    return (
      <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--accent-amber)', textAlign: 'center', padding: '2.5rem' }}>
          <ShieldAlert size={44} style={{ color: 'var(--accent-amber)', margin: '0 auto 1rem' }} />
          <h2>Nutrition Features Paused</h2>
          <p style={{ marginTop: '0.5rem' }}>
            In accordance with Rule S7, meal plan generation and nutrition displays are currently switched off.
          </p>
        </div>
      </div>
    )
  }

  if (!isAdultConfirmed) {
    return (
      <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)', textAlign: 'center', padding: '2.5rem' }}>
          <AlertTriangle size={44} style={{ color: 'var(--accent-primary)', margin: '0 auto 1rem' }} />
          <h2>Age Confirmation Required (Rule S2)</h2>
          <p style={{ marginTop: '0.5rem' }}>
            Please confirm your adult age status in the Nutrition Targets section to access meal plan generation.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Header & Controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Calendar style={{ color: 'var(--accent-primary)' }} />
            7-Day Meal Plans
          </h1>
          <p style={{ marginTop: '0.25rem' }}>
            Deterministic, allergen-safe 7-day meal plans with transparent heuristics
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {plans.length > 0 && (
            <select
              className="input"
              value={selectedPlanId || ''}
              onChange={(e) => handleSelectPlan(e.target.value)}
              style={{ width: 'auto', minWidth: '180px' }}
              aria-label="Select saved meal plan"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.start_date})
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowGeneratorModal(true)}
          >
            <Sparkles size={16} />
            <span>Generate Plan</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div
          style={{
            background: 'var(--accent-rose-bg)',
            border: '1px solid var(--accent-rose-border)',
            color: 'var(--accent-rose)',
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-md)',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
          role="alert"
        >
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Infeasible Explanation Card (AC-62, AC-72) */}
      {infeasibleData && (
        <div
          className="card"
          style={{
            marginBottom: '2rem',
            borderLeft: '4px solid var(--accent-rose)',
            background: 'var(--bg-surface-elevated)',
          }}
          role="alert"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <ShieldAlert size={28} style={{ color: 'var(--accent-rose)' }} />
            <div>
              <h2 style={{ fontSize: '1.25rem', color: 'var(--accent-rose)' }}>Plan Infeasible</h2>
              <p style={{ fontSize: '0.875rem' }}>
                No recipe in the catalogue satisfied all hard filters for slot{' '}
                <strong style={{ color: 'var(--text-primary)' }}>{infeasibleData.slot}</strong> on{' '}
                <strong style={{ color: 'var(--text-primary)' }}>{infeasibleData.day}</strong>.
              </p>
            </div>
          </div>

          <p style={{ fontSize: '0.9375rem', marginBottom: '1rem' }}>{infeasibleData.message}</p>

          <h3 style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Recipes Removed By Hard Filter:
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
            {infeasibleData.filters.map((f, idx) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-surface)',
                  padding: '0.625rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ fontSize: '0.875rem' }}>{f.filter}</span>
                <span style={{ fontWeight: 600, color: 'var(--accent-rose)' }}>-{f.removed}</span>
              </div>
            ))}
          </div>

          <div
            style={{
              padding: '0.75rem 1rem',
              background: 'var(--accent-amber-bg)',
              border: '1px solid var(--accent-amber-border)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
              color: 'var(--accent-amber)',
            }}
          >
            <strong>Safety & Relaxation Notice:</strong>{' '}
            {infeasibleData.relaxable.length > 0 ? (
              <span>
                You can consider adjusting your non-safety caps: <strong>{infeasibleData.relaxable.join(', ')}</strong>.
              </span>
            ) : (
              <span>No user caps were active.</span>
            )}{' '}
            Allergies and diet restrictions are hard clinical safeguards and can never be relaxed by the algorithm.
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="card" style={{ padding: '3rem 2rem', textAlign: 'center' }}>
          <div className="skeleton" style={{ height: '28px', width: '220px', margin: '0 auto 1rem', borderRadius: '4px' }} />
          <div className="skeleton" style={{ height: '300px', width: '100%', borderRadius: '8px' }} />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !currentPlan && !infeasibleData && (
        <div className="card" style={{ padding: '3rem 2rem', textAlign: 'center' }}>
          <ChefHat size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
          <h2>No Meal Plans Generated Yet</h2>
          <p style={{ maxWidth: '460px', margin: '0.5rem auto 1.5rem', color: 'var(--text-secondary)' }}>
            Generate your first 7-day strength meal plan matching your macro targets, food exclusions, and allergen safeguards.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowGeneratorModal(true)}
          >
            <Sparkles size={16} />
            <span>Generate 7-Day Plan</span>
          </button>
        </div>
      )}

      {/* Main 7-Day Plan View */}
      {!isLoading && currentPlan && (
        <div>
          {/* Plan Info Banner */}
          <div
            className="card"
            style={{
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
              padding: '1rem 1.25rem',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h2 style={{ fontSize: '1.25rem' }}>{currentPlan.name}</h2>
                <span
                  style={{
                    background: 'var(--accent-emerald-bg)',
                    color: 'var(--accent-emerald)',
                    padding: '0.125rem 0.5rem',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                  }}
                >
                  Version {currentPlan.generation_version}
                </span>
              </div>
              <p style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
                {currentPlan.start_date} to {currentPlan.end_date}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setShowExplanation(!showExplanation)}
              >
                <Info size={14} />
                <span>{showExplanation ? 'Hide Heuristics' : 'View Heuristics (AC-72)'}</span>
                {showExplanation ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleDeletePlan(currentPlan.id)}
                title="Delete this meal plan"
                aria-label="Delete plan"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>

          {/* Explanation Panel (AC-72) */}
          {showExplanation && currentPlan.explanation && (
            <div
              className="card"
              style={{
                marginBottom: '1.5rem',
                borderLeft: '4px solid var(--accent-primary)',
                background: 'var(--bg-surface-elevated)',
              }}
            >
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} />
                Deterministic Scoring & Heuristics (Rule S4, AC-72)
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                {currentPlan.explanation.statement}
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Target Fit Weight (w_t)</div>
                  <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>{currentPlan.explanation.scoring_weights.w_t}</div>
                </div>
                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Cuisine Match Weight (w_c)</div>
                  <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>{currentPlan.explanation.scoring_weights.w_c}</div>
                </div>
                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Prep Time Penalty (w_p)</div>
                  <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>{currentPlan.explanation.scoring_weights.w_p}</div>
                </div>
                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Repetition Penalty (w_r)</div>
                  <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>{currentPlan.explanation.scoring_weights.w_r}</div>
                </div>
              </div>

              <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                Catalogue Version: {currentPlan.explanation.catalog_version} • Discrete Serving Sizes: 0.5, 1.0, 1.5, 2.0, 2.5, 3.0
              </div>
            </div>
          )}

          {/* Warnings List (AC-61, AC-67) */}
          {currentPlan.warnings && currentPlan.warnings.length > 0 && (
            <div
              style={{
                background: 'var(--accent-amber-bg)',
                border: '1px solid var(--accent-amber-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem 1rem',
                marginBottom: '1.5rem',
              }}
              role="alert"
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-amber)', fontWeight: 600, marginBottom: '0.25rem' }}>
                <AlertTriangle size={16} />
                <span>Plan Notices ({currentPlan.warnings.length})</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: 'var(--accent-amber)' }}>
                {currentPlan.warnings.map((w: any, idx: number) => (
                  <li key={idx}>
                    {w.warning === 'target_deviation' && (
                      <span>
                        Day <strong>{w.day}</strong>: {w.metric} deviation of {w.difference_pct > 0 ? `+${w.difference_pct}%` : `${w.difference_pct}%`} (target: {w.target}, planned: {w.actual})
                      </span>
                    )}
                    {w.warning === 'cuisine_preference_unmet' && (
                      <span>{w.message}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 7-Day Grid */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {currentPlan.days &&
              currentPlan.days.map((day: any) => {
                const dayMeals = currentPlan.meals.filter((m: any) => m.plan_date === day.plan_date)
                const hasDeviation = day.deviations && day.deviations.length > 0

                return (
                  <div
                    key={day.plan_date}
                    className="card"
                    style={{
                      borderLeft: hasDeviation ? '4px solid var(--accent-amber)' : '4px solid var(--border-subtle)',
                      padding: '1.25rem',
                    }}
                  >
                    {/* Day Header */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '0.75rem',
                        marginBottom: '1rem',
                        borderBottom: '1px solid var(--border-subtle)',
                        paddingBottom: '0.75rem',
                      }}
                    >
                      <div>
                        <h3 style={{ fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span>{day.plan_date}</span>
                          {hasDeviation && (
                            <span
                              style={{
                                background: 'var(--accent-amber-bg)',
                                color: 'var(--accent-amber)',
                                fontSize: '0.75rem',
                                padding: '0.125rem 0.5rem',
                                borderRadius: '12px',
                                fontWeight: 500,
                              }}
                            >
                              Target Deviation (AC-67)
                            </span>
                          )}
                        </h3>
                      </div>

                      {/* Day Totals Summary */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        {!isCaloriesHidden && (
                          <div
                            style={{
                              background: 'var(--bg-surface-elevated)',
                              padding: '0.25rem 0.625rem',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.875rem',
                            }}
                          >
                            <span style={{ color: 'var(--text-secondary)', marginRight: '0.25rem' }}>Calories:</span>
                            <strong>{Math.round(day.calories)}</strong>
                            {day.calorie_target && (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                {' '}/ {day.calorie_target} kcal
                              </span>
                            )}
                          </div>
                        )}

                        <div
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            padding: '0.25rem 0.625rem',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.875rem',
                          }}
                        >
                          <span style={{ color: 'var(--text-secondary)', marginRight: '0.25rem' }}>Protein:</span>
                          <strong style={{ color: 'var(--accent-primary)' }}>{Math.round(day.protein_g)}g</strong>
                          {day.protein_target && (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                              {' '}/ {day.protein_target}g
                            </span>
                          )}
                        </div>

                        <div
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            padding: '0.25rem 0.625rem',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.875rem',
                          }}
                        >
                          <span style={{ color: 'var(--text-secondary)', marginRight: '0.25rem' }}>Carbs:</span>
                          <strong>{Math.round(day.carbs_g)}g</strong>
                        </div>

                        <div
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            padding: '0.25rem 0.625rem',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.875rem',
                          }}
                        >
                          <span style={{ color: 'var(--text-secondary)', marginRight: '0.25rem' }}>Fat:</span>
                          <strong>{Math.round(day.fat_g)}g</strong>
                        </div>
                      </div>
                    </div>

                    {/* Meals for this day */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                      {dayMeals.map((meal: any) => (
                        <div
                          key={meal.id}
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--border-subtle)',
                            padding: '0.875rem 1rem',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '0.375rem',
                              }}
                            >
                              <span
                                style={{
                                  fontSize: '0.75rem',
                                  textTransform: 'uppercase',
                                  fontWeight: 600,
                                  color: 'var(--accent-primary)',
                                  letterSpacing: '0.05em',
                                }}
                              >
                                {meal.meal_type}
                              </span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {meal.servings} serving{meal.servings > 1 ? 's' : ''}
                              </span>
                            </div>

                            <h4 style={{ fontSize: '1rem', marginBottom: '0.5rem', lineHeight: 1.3 }}>
                              {meal.title}
                            </h4>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                              {meal.total_minutes > 0 && (
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                  <Clock size={12} />
                                  {meal.total_minutes}m
                                </span>
                              )}
                              {meal.cuisine_code && (
                                <span
                                  style={{
                                    background: 'var(--bg-surface)',
                                    padding: '0.125rem 0.375rem',
                                    borderRadius: '4px',
                                    textTransform: 'capitalize',
                                  }}
                                >
                                  {meal.cuisine_code}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Meal Nutrients */}
                          <div
                            style={{
                              borderTop: '1px solid var(--border-subtle)',
                              paddingTop: '0.5rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '0.8125rem',
                            }}
                          >
                            {!isCaloriesHidden && (
                              <span>
                                <strong>{Math.round(meal.nutrients.calories)}</strong> kcal
                              </span>
                            )}
                            <span style={{ color: 'var(--accent-primary)' }}>
                              <strong>{Math.round(meal.nutrients.protein_g)}g</strong> P
                            </span>
                            <span>
                              <strong>{Math.round(meal.nutrients.carbs_g)}g</strong> C
                            </span>
                            <span>
                              <strong>{Math.round(meal.nutrients.fat_g)}g</strong> F
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Disclaimer Banner (Rule S1, AC-72) */}
          <div
            style={{
              marginTop: '2rem',
              padding: '1rem',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.8125rem',
              color: 'var(--text-muted)',
              textAlign: 'center',
            }}
          >
            {currentPlan.disclaimer}
          </div>
        </div>
      )}

      {/* Generator Modal */}
      {showGeneratorModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="generator-title"
        >
          <div
            className="card"
            style={{
              maxWidth: '520px',
              width: '100%',
              padding: '1.75rem',
              background: 'var(--bg-surface)',
            }}
          >
            <h2 id="generator-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Sparkles style={{ color: 'var(--accent-primary)' }} />
              Generate 7-Day Meal Plan
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              Configure slot targets and user caps. Safety filters (allergies, diet tags, exclusions) are applied automatically.
            </p>

            <form onSubmit={handleGenerate}>
              <div style={{ marginBottom: '1rem' }}>
                <label className="label" htmlFor="start-date-input">
                  Start Date
                </label>
                <input
                  id="start-date-input"
                  type="date"
                  className="input"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label className="label" htmlFor="days-count-input">
                  Duration (Days)
                </label>
                <input
                  id="days-count-input"
                  type="number"
                  className="input"
                  value={daysCount}
                  onChange={(e) => setDaysCount(Number(e.target.value))}
                  min={1}
                  max={14}
                  required
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label className="label">Meal Slots</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {['breakfast', 'lunch', 'dinner', 'snack'].map((slot) => {
                    const isSelected = selectedSlots.includes(slot)
                    return (
                      <button
                        type="button"
                        key={slot}
                        className={`btn btn-sm ${isSelected ? 'btn-primary' : 'btn-ghost'}`}
                        onClick={() => toggleSlot(slot)}
                        style={{ textTransform: 'capitalize' }}
                      >
                        {slot}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                <div>
                  <label className="label" htmlFor="max-minutes-input">
                    Max Prep Time (mins)
                  </label>
                  <input
                    id="max-minutes-input"
                    type="number"
                    className="input"
                    placeholder="e.g. 30 (optional)"
                    value={maxMinutes}
                    onChange={(e) => setMaxMinutes(e.target.value)}
                    min={5}
                    max={180}
                  />
                </div>

                <div>
                  <label className="label" htmlFor="daily-budget-input">
                    Daily Budget (INR)
                  </label>
                  <input
                    id="daily-budget-input"
                    type="number"
                    className="input"
                    placeholder="e.g. 500 (optional)"
                    value={dailyBudget}
                    onChange={(e) => setDailyBudget(e.target.value)}
                    min={0}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowGeneratorModal(false)}
                  disabled={isGenerating}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isGenerating}>
                  <Sparkles size={16} />
                  <span>{isGenerating ? 'Generating...' : 'Generate Plan'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
