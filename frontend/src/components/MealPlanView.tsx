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
  ShoppingCart,
  RefreshCw,
  Sliders,
  Check,
  CheckSquare,
  Square,
  X,
  Filter,
  Copy,
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

  // Substitution state (AC-73, AC-74, AC-75)
  const [activeMealForSub, setActiveMealForSub] = useState<any | null>(null)
  const [subSuggestions, setSubSuggestions] = useState<any[]>([])
  const [isLoadingSubs, setIsLoadingSubs] = useState(false)
  const [subError, setSubError] = useState<string | null>(null)
  const [selectedSubServings, setSelectedSubServings] = useState<Record<string, number>>({})
  const [isAcceptingSub, setIsAcceptingSub] = useState(false)

  // Servings quick edit state (AC-76)
  const [activeMealForServings, setActiveMealForServings] = useState<any | null>(null)
  const [editServingsValue, setEditServingsValue] = useState<number>(1.0)
  const [isSavingServings, setIsSavingServings] = useState(false)
  const [servingsError, setServingsError] = useState<string | null>(null)

  // Grocery list modal state (AC-77 to AC-81)
  const [showGroceryModal, setShowGroceryModal] = useState(false)
  const [groceryFromDate, setGroceryFromDate] = useState<string>('')
  const [groceryToDate, setGroceryToDate] = useState<string>('')
  const [groceryList, setGroceryList] = useState<any | null>(null)
  const [isLoadingGrocery, setIsLoadingGrocery] = useState(false)
  const [checkedGroceryItems, setCheckedGroceryItems] = useState<Record<string, boolean>>({})
  const [copiedNotice, setCopiedNotice] = useState(false)

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

  // --- Step 9 Substitution Handlers (AC-73, AC-74, AC-75) ---
  const handleOpenSubstitute = async (meal: any) => {
    if (!currentPlan) return
    setActiveMealForSub(meal)
    setSubSuggestions([])
    setSubError(null)
    setIsLoadingSubs(true)

    try {
      const suggestions = await api.suggestSubstitutions(currentPlan.id, meal.id)
      setSubSuggestions(suggestions)
      const initialServings: Record<string, number> = {}
      suggestions.forEach((s: any) => {
        initialServings[s.recipe_id] = Number(s.servings) || 1.0
      })
      setSelectedSubServings(initialServings)
    } catch (err: any) {
      setSubError(err.message || 'Could not fetch substitution suggestions.')
    } finally {
      setIsLoadingSubs(false)
    }
  }

  const handleAcceptSubstitution = async (recipeId: string) => {
    if (!currentPlan || !activeMealForSub) return
    setIsAcceptingSub(true)
    setSubError(null)

    try {
      const servings = selectedSubServings[recipeId] || 1.0
      const updatedPlan = await api.acceptSubstitution(
        currentPlan.id,
        activeMealForSub.id,
        recipeId,
        servings
      )
      setCurrentPlan(updatedPlan)
      setActiveMealForSub(null)
      await loadPlans()
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 422) {
        setSubError('Cannot substitute: this recipe violates your allergy or diet constraints (Rule S9, AC-75).')
      } else {
        setSubError(err.message || 'Failed to accept substitution.')
      }
    } finally {
      setIsAcceptingSub(false)
    }
  }

  // --- Step 9 Servings Edit Handlers (AC-76) ---
  const handleOpenEditServings = (meal: any) => {
    setActiveMealForServings(meal)
    setEditServingsValue(Number(meal.servings) || 1.0)
    setServingsError(null)
  }

  const handleSaveServings = async () => {
    if (!currentPlan || !activeMealForServings) return
    if (editServingsValue < 0.5 || editServingsValue > 10.0) {
      setServingsError('Servings must be between 0.5 and 10.0 (AC-76).')
      return
    }

    setIsSavingServings(true)
    setServingsError(null)

    try {
      const updatedPlan = await api.editPlannedMeal(
        currentPlan.id,
        activeMealForServings.id,
        { servings: editServingsValue }
      )
      setCurrentPlan(updatedPlan)
      setActiveMealForServings(null)
    } catch (err: any) {
      setServingsError(err.message || 'Failed to update servings.')
    } finally {
      setIsSavingServings(false)
    }
  }

  // --- Step 9 Grocery List Handlers (AC-77 to AC-81) ---
  const handleOpenGroceryList = async () => {
    if (!currentPlan) return
    setShowGroceryModal(true)
    setGroceryFromDate(currentPlan.start_date || '')
    setGroceryToDate(currentPlan.end_date || '')
    await loadGroceryList(currentPlan.start_date, currentPlan.end_date)
  }

  const loadGroceryList = async (from?: string, to?: string) => {
    if (!currentPlan) return
    setIsLoadingGrocery(true)
    try {
      const res = await api.getGroceryList(currentPlan.id, from || undefined, to || undefined)
      setGroceryList(res)
    } catch (err: any) {
      console.error('Could not load grocery list:', err)
    } finally {
      setIsLoadingGrocery(false)
    }
  }

  const toggleGroceryChecked = (key: string) => {
    setCheckedGroceryItems((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const handleCopyChecklist = () => {
    if (!groceryList || !groceryList.items) return
    const lines = groceryList.items.map((it: any) => {
      const checked = checkedGroceryItems[it.name] ? '[x]' : '[ ]'
      return `${checked} ${it.name} - ${it.display_quantity} (${it.category})`
    })
    navigator.clipboard.writeText(lines.join('\n'))
    setCopiedNotice(true)
    setTimeout(() => setCopiedNotice(false), 2000)
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
                  {p.name} ({p.start_date}) {p.status === 'edited' ? '• Edited' : ''}
                </option>
              ))}
            </select>
          )}

          {currentPlan && (
            <button
              id="btn-open-grocery-list"
              type="button"
              className="btn btn-secondary"
              onClick={handleOpenGroceryList}
              title="View Unit-Aware Grocery List (AC-77 to AC-81)"
            >
              <ShoppingCart size={16} />
              <span>Grocery List</span>
            </button>
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
            background: 'var(--accent-danger-bg)',
            border: '1px solid var(--accent-danger-border)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}
          role="alert"
        >
          <AlertTriangle size={20} style={{ color: 'var(--accent-danger)' }} />
          <div>{errorMsg}</div>
        </div>
      )}

      {/* Infeasible Generation Result (Rule S4, AC-62, AC-72) */}
      {infeasibleData && (
        <div
          className="card"
          style={{
            borderLeft: '4px solid var(--accent-amber)',
            marginBottom: '2rem',
            padding: '1.5rem',
            background: 'var(--bg-surface-elevated)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <AlertTriangle size={24} style={{ color: 'var(--accent-amber)' }} />
            <div>
              <h2 style={{ fontSize: '1.25rem' }}>Generation Infeasible</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                Slot: <strong style={{ textTransform: 'capitalize' }}>{infeasibleData.slot}</strong> on{' '}
                <strong>{infeasibleData.day}</strong>
              </p>
            </div>
          </div>

          <p style={{ marginBottom: '1rem' }}>{infeasibleData.message}</p>

          <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Pruned Constraints Breakdown:</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
            {infeasibleData.filters.map((f, i) => (
              <div
                key={i}
                style={{
                  background: 'var(--bg-surface)',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  {f.filter.replace('_', ' ')}
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--accent-amber)' }}>
                  {f.removed} recipes removed
                </div>
              </div>
            ))}
          </div>

          {infeasibleData.relaxable && infeasibleData.relaxable.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                Suggested Soft Constraints to Relax:
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                {infeasibleData.relaxable.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Main Plan Display */}
      {isLoading ? (
        <div className="card skeleton-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="skeleton-pulse" style={{ height: '24px', width: '30%', margin: '0 auto 1rem' }} />
          <div className="skeleton-pulse" style={{ height: '16px', width: '60%', margin: '0 auto' }} />
        </div>
      ) : !currentPlan ? (
        <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
          <ChefHat size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
          <h2>No Meal Plans Generated Yet</h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0.5rem auto 1.5rem' }}>
            Generate a full 7-day meal plan tailored to your strength and protein targets with zero hallucinated foods.
          </p>
          <button className="btn btn-primary" onClick={() => setShowGeneratorModal(true)}>
            <Sparkles size={16} />
            <span>Generate Your First Plan</span>
          </button>
        </div>
      ) : (
        <div>
          {/* Plan Meta Banner */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.25rem',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div>
              <h2 style={{ fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>{currentPlan.name}</span>
                {currentPlan.status === 'edited' && (
                  <span
                    style={{
                      background: 'var(--accent-cyan-bg, rgba(6,182,212,0.15))',
                      color: 'var(--accent-cyan, #06b6d4)',
                      fontSize: '0.75rem',
                      padding: '0.125rem 0.5rem',
                      borderRadius: '12px',
                      fontWeight: 600,
                    }}
                  >
                    Edited (AC-74)
                  </span>
                )}
              </h2>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                {currentPlan.start_date} to {currentPlan.end_date} • Engine v{currentPlan.generation_version}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                className="btn btn-sm btn-ghost"
                onClick={() => setShowExplanation(!showExplanation)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                aria-expanded={showExplanation}
              >
                <Info size={14} />
                <span>Heuristics</span>
                {showExplanation ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              <button
                className="btn btn-sm btn-ghost text-danger"
                onClick={() => handleDeletePlan(currentPlan.id)}
                title="Delete Meal Plan"
                aria-label="Delete Meal Plan"
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
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
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
                                {meal.servings} serving{Number(meal.servings) > 1 ? 's' : ''}
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
                          <div>
                            <div
                              style={{
                                borderTop: '1px solid var(--border-subtle)',
                                paddingTop: '0.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                fontSize: '0.8125rem',
                                marginBottom: '0.5rem',
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

                            {/* Actions: Substitute & Adjust Servings (AC-73, AC-76) */}
                            <div
                              style={{
                                display: 'flex',
                                gap: '0.5rem',
                                borderTop: '1px solid var(--border-subtle)',
                                paddingTop: '0.5rem',
                              }}
                            >
                              <button
                                id={`btn-substitute-${meal.id}`}
                                type="button"
                                className="btn btn-xs btn-ghost"
                                onClick={() => handleOpenSubstitute(meal)}
                                style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}
                                title="Substitute with recipe matching slot target (AC-73)"
                              >
                                <RefreshCw size={12} />
                                <span>Substitute</span>
                              </button>
                              <button
                                id={`btn-edit-servings-${meal.id}`}
                                type="button"
                                className="btn btn-xs btn-ghost"
                                onClick={() => handleOpenEditServings(meal)}
                                style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}
                                title="Adjust meal servings (AC-76)"
                              >
                                <Sliders size={12} />
                                <span>{meal.servings}x Servings</span>
                              </button>
                            </div>
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
              color: 'var(--text-secondary)',
              lineHeight: 1.4,
            }}
          >
            <strong>Informational Disclaimer (Rule S1):</strong> {currentPlan.disclaimer}
          </div>
        </div>
      )}

      {/* --- Step 9: Substitution Modal (AC-73 to AC-75) --- */}
      {activeMealForSub && (
        <div className="modal-backdrop" onClick={() => setActiveMealForSub(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '640px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <RefreshCw size={18} style={{ color: 'var(--accent-primary)' }} />
                  Substitute Planned Meal
                </h2>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  Replacing <strong>{activeMealForSub.title}</strong> ({activeMealForSub.meal_type}) on{' '}
                  {activeMealForSub.plan_date}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setActiveMealForSub(null)}
                aria-label="Close modal"
              >
                <X size={16} />
              </button>
            </div>

            {subError && (
              <div
                style={{
                  background: 'var(--accent-danger-bg)',
                  border: '1px solid var(--accent-danger-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem 1rem',
                  marginBottom: '1rem',
                  fontSize: '0.875rem',
                  color: 'var(--accent-danger)',
                }}
                role="alert"
              >
                {subError}
              </div>
            )}

            {isLoadingSubs ? (
              <div style={{ padding: '2.5rem', textAlign: 'center' }}>
                <div className="skeleton-pulse" style={{ height: '20px', width: '50%', margin: '0 auto 1rem' }} />
                <div className="skeleton-pulse" style={{ height: '60px', width: '100%', marginBottom: '0.75rem' }} />
                <div className="skeleton-pulse" style={{ height: '60px', width: '100%' }} />
              </div>
            ) : subSuggestions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-secondary)' }}>
                No eligible replacement recipes found that respect your allergen constraints and slot targets.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '420px', overflowY: 'auto' }}>
                {subSuggestions.map((s) => {
                  const sServ = selectedSubServings[s.recipe_id] || Number(s.servings) || 1.0
                  const diff = s.nutrient_diff || {}

                  return (
                    <div
                      key={s.recipe_id}
                      style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.5rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem' }}>
                        <div>
                          <h4 style={{ fontSize: '1rem', marginBottom: '0.25rem' }}>{s.recipe_name}</h4>
                          <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            <span style={{ textTransform: 'capitalize' }}>{s.cuisine_code}</span>
                            <span>•</span>
                            <span>{s.total_minutes} mins</span>
                            <span>•</span>
                            <span>Fit Score: {Math.round(Number(s.score) * 100) / 100}</span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <select
                            className="input"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.8125rem', width: 'auto' }}
                            value={sServ}
                            onChange={(e) =>
                              setSelectedSubServings((prev) => ({
                                ...prev,
                                [s.recipe_id]: Number(e.target.value),
                              }))
                            }
                            aria-label="Select servings for substitution"
                          >
                            {[0.5, 1.0, 1.5, 2.0, 2.5, 3.0].map((num) => (
                              <option key={num} value={num}>
                                {num}x
                              </option>
                            ))}
                          </select>

                          <button
                            id={`btn-accept-sub-${s.recipe_id}`}
                            type="button"
                            className="btn btn-sm btn-primary"
                            onClick={() => handleAcceptSubstitution(s.recipe_id)}
                            disabled={isAcceptingSub}
                          >
                            <Check size={14} />
                            <span>Select</span>
                          </button>
                        </div>
                      </div>

                      {/* Nutrient Difference Badges (AC-73) */}
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem' }}>
                        {!isCaloriesHidden && (
                          <span
                            style={{
                              background: 'var(--bg-surface-elevated)',
                              padding: '0.125rem 0.375rem',
                              borderRadius: '4px',
                            }}
                          >
                            Cal: {Math.round(Number(s.nutrients.calories))} (
                            <span style={{ color: Number(diff.calories) >= 0 ? 'var(--accent-amber)' : 'var(--accent-primary)' }}>
                              {Number(diff.calories) >= 0 ? `+${Math.round(Number(diff.calories))}` : Math.round(Number(diff.calories))}
                            </span>
                            )
                          </span>
                        )}
                        <span
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            padding: '0.125rem 0.375rem',
                            borderRadius: '4px',
                          }}
                        >
                          Protein: {Math.round(Number(s.nutrients.protein_g))}g (
                          <span style={{ color: Number(diff.protein_g) >= 0 ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                            {Number(diff.protein_g) >= 0 ? `+${Math.round(Number(diff.protein_g))}` : Math.round(Number(diff.protein_g))}g
                          </span>
                          )
                        </span>
                        <span
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            padding: '0.125rem 0.375rem',
                            borderRadius: '4px',
                          }}
                        >
                          Carbs: {Math.round(Number(s.nutrients.carbs_g))}g (
                          <span>
                            {Number(diff.carbs_g) >= 0 ? `+${Math.round(Number(diff.carbs_g))}` : Math.round(Number(diff.carbs_g))}g
                          </span>
                          )
                        </span>
                        <span
                          style={{
                            background: 'var(--bg-surface-elevated)',
                            padding: '0.125rem 0.375rem',
                            borderRadius: '4px',
                          }}
                        >
                          Fat: {Math.round(Number(s.nutrients.fat_g))}g (
                          <span>
                            {Number(diff.fat_g) >= 0 ? `+${Math.round(Number(diff.fat_g))}` : Math.round(Number(diff.fat_g))}g
                          </span>
                          )
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- Step 9: Servings Adjustment Modal (AC-76) --- */}
      {activeMealForServings && (
        <div className="modal-backdrop" onClick={() => setActiveMealForServings(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '440px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sliders size={18} style={{ color: 'var(--accent-primary)' }} />
                Adjust Servings (AC-76)
              </h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setActiveMealForServings(null)}
                aria-label="Close modal"
              >
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              Scale quantities and nutrients linearly for <strong>{activeMealForServings.title}</strong>. Allowed range: 0.5 to 10.0 servings.
            </p>

            {servingsError && (
              <div
                style={{
                  background: 'var(--accent-danger-bg)',
                  border: '1px solid var(--accent-danger-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem',
                  marginBottom: '1rem',
                  fontSize: '0.875rem',
                  color: 'var(--accent-danger)',
                }}
                role="alert"
              >
                {servingsError}
              </div>
            )}

            <div style={{ marginBottom: '1.25rem' }}>
              <label className="label" htmlFor="servings-input">
                Servings Multiplier
              </label>
              <input
                id="servings-input"
                type="number"
                step="0.5"
                min="0.5"
                max="10.0"
                className="input"
                value={editServingsValue}
                onChange={(e) => setEditServingsValue(Number(e.target.value))}
              />

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                {[0.5, 1.0, 1.5, 2.0, 3.0, 4.0].map((v) => (
                  <button
                    key={v}
                    type="button"
                    className={`btn btn-xs ${editServingsValue === v ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={() => setEditServingsValue(v)}
                  >
                    {v}x
                  </button>
                ))}
              </div>
            </div>

            {/* Nutrients Preview */}
            <div
              style={{
                background: 'var(--bg-surface)',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                marginBottom: '1.25rem',
                fontSize: '0.875rem',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              {!isCaloriesHidden && (
                <span>
                  Calories:{' '}
                  <strong>
                    {Math.round(
                      (Number(activeMealForServings.nutrients.calories) * editServingsValue) /
                        Number(activeMealForServings.servings)
                    )}
                  </strong>{' '}
                  kcal
                </span>
              )}
              <span>
                Protein:{' '}
                <strong style={{ color: 'var(--accent-primary)' }}>
                  {Math.round(
                    (Number(activeMealForServings.nutrients.protein_g) * editServingsValue) /
                      Number(activeMealForServings.servings)
                  )}
                  g
                </strong>
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setActiveMealForServings(null)}
                disabled={isSavingServings}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-save-servings"
                type="button"
                className="btn btn-primary"
                onClick={handleSaveServings}
                disabled={isSavingServings}
              >
                {isSavingServings ? 'Saving...' : 'Apply Servings'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- Step 9: Grocery List Modal (AC-77 to AC-81) --- */}
      {showGroceryModal && currentPlan && (
        <div className="modal-backdrop" onClick={() => setShowGroceryModal(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '680px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ShoppingCart size={20} style={{ color: 'var(--accent-primary)' }} />
                  Unit-Aware Grocery List
                </h2>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  Scaled ingredient quantities aggregated by unit family and categorized (AC-77 to AC-81)
                </p>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowGroceryModal(false)}
                aria-label="Close modal"
              >
                <X size={16} />
              </button>
            </div>

            {/* Date Filtering Bar (AC-80) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                flexWrap: 'wrap',
                background: 'var(--bg-surface)',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                marginBottom: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>From:</span>
                <input
                  id="grocery-from-date"
                  type="date"
                  className="input"
                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.8125rem' }}
                  value={groceryFromDate}
                  min={currentPlan.start_date}
                  max={currentPlan.end_date}
                  onChange={(e) => setGroceryFromDate(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>To:</span>
                <input
                  id="grocery-to-date"
                  type="date"
                  className="input"
                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.8125rem' }}
                  value={groceryToDate}
                  min={currentPlan.start_date}
                  max={currentPlan.end_date}
                  onChange={(e) => setGroceryToDate(e.target.value)}
                />
              </div>

              <button
                id="btn-filter-grocery"
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={() => loadGroceryList(groceryFromDate, groceryToDate)}
                disabled={isLoadingGrocery}
              >
                <Filter size={12} />
                <span>Filter</span>
              </button>

              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={handleCopyChecklist}
                style={{ marginLeft: 'auto' }}
                title="Copy checklist to clipboard"
              >
                <Copy size={12} />
                <span>{copiedNotice ? 'Copied!' : 'Copy'}</span>
              </button>
            </div>

            {/* Grocery Checklist Grouped by Category (AC-81) */}
            {isLoadingGrocery ? (
              <div style={{ padding: '2.5rem', textAlign: 'center' }}>
                <div className="skeleton-pulse" style={{ height: '24px', width: '40%', margin: '0 auto 1rem' }} />
                <div className="skeleton-pulse" style={{ height: '40px', width: '100%', marginBottom: '0.5rem' }} />
                <div className="skeleton-pulse" style={{ height: '40px', width: '100%', marginBottom: '0.5rem' }} />
                <div className="skeleton-pulse" style={{ height: '40px', width: '100%' }} />
              </div>
            ) : !groceryList || groceryList.items.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-secondary)' }}>
                No ingredients found for the selected date range.
              </div>
            ) : (
              <div style={{ maxHeight: '420px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {Object.entries(
                  groceryList.items.reduce((acc: Record<string, any[]>, item: any) => {
                    const cat = item.is_text_only ? 'Additional Items' : item.category || 'General'
                    if (!acc[cat]) acc[cat] = []
                    acc[cat].push(item)
                    return acc
                  }, {})
                ).map(([category, items]: [string, any]) => (
                  <div key={category}>
                    <h3
                      style={{
                        fontSize: '0.875rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: 'var(--accent-primary)',
                        marginBottom: '0.5rem',
                        borderBottom: '1px solid var(--border-subtle)',
                        paddingBottom: '0.25rem',
                      }}
                    >
                      {category} ({items.length})
                    </h3>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                      {items.map((item: any, idx: number) => {
                        const itemKey = `${item.name}-${item.display_quantity}`
                        const isChecked = checkedGroceryItems[itemKey] || false

                        return (
                          <div
                            key={idx}
                            onClick={() => toggleGroceryChecked(itemKey)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '0.5rem 0.75rem',
                              background: isChecked ? 'transparent' : 'var(--bg-surface)',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid var(--border-subtle)',
                              cursor: 'pointer',
                              opacity: isChecked ? 0.5 : 1,
                              transition: 'opacity 0.15s ease',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                              {isChecked ? (
                                <CheckSquare size={16} style={{ color: 'var(--accent-primary)' }} />
                              ) : (
                                <Square size={16} style={{ color: 'var(--text-muted)' }} />
                              )}
                              <span
                                style={{
                                  fontSize: '0.875rem',
                                  textDecoration: isChecked ? 'line-through' : 'none',
                                }}
                              >
                                {item.name}
                              </span>
                            </div>

                            <span
                              style={{
                                fontSize: '0.8125rem',
                                fontWeight: 600,
                                color: 'var(--text-secondary)',
                                textDecoration: isChecked ? 'line-through' : 'none',
                              }}
                            >
                              {item.display_quantity}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- Plan Generator Modal (AC-56 to AC-60) --- */}
      {showGeneratorModal && (
        <div className="modal-backdrop" onClick={() => setShowGeneratorModal(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '520px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={20} style={{ color: 'var(--accent-primary)' }} />
                Generate 7-Day Meal Plan
              </h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowGeneratorModal(false)}
                aria-label="Close modal"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleGenerate}>
              <div style={{ marginBottom: '1rem' }}>
                <label className="label" htmlFor="plan-start-date">
                  Start Date
                </label>
                <input
                  id="plan-start-date"
                  type="date"
                  className="input"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label className="label" htmlFor="plan-days-count">
                  Duration (Days)
                </label>
                <input
                  id="plan-days-count"
                  type="number"
                  className="input"
                  value={daysCount}
                  onChange={(e) => setDaysCount(Number(e.target.value))}
                  min={1}
                  max={7}
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
