import React, { useState, useEffect, useCallback } from 'react'
import { Utensils, Shield, Calculator, AlertCircle, Check, Heart, Sliders } from 'lucide-react'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

const EU_ALLERGENS = [
  'cereals_gluten',
  'crustaceans',
  'eggs',
  'fish',
  'peanuts',
  'soybeans',
  'milk',
  'tree_nuts',
  'celery',
  'mustard',
  'sesame',
  'sulphites',
  'lupin',
  'molluscs',
]

const DIET_TAGS = [
  'vegan',
  'vegetarian',
  'pescatarian',
  'halal',
  'kosher',
  'gluten_free',
  'dairy_free',
]

const CUISINES = ['indian', 'italian', 'mexican', 'american', 'east_asian', 'mediterranean']

export const NutritionPlanner: React.FC = () => {
  const { profile, confirmAdult, refreshProfile } = useAuth()
  const isCaloriesHidden = profile?.calories_hidden || false
  const isNutritionPaused = profile?.nutrition_paused || false
  const isAdultConfirmed = !!profile?.adult_confirmed_at

  const [activeTab, setActiveTab] = useState<'targets' | 'estimate' | 'preferences'>('targets')

  // Target state
  const [activeGoal, setActiveGoal] = useState<any | null>(null)
  const [manualKcal, setManualKcal] = useState<number | string>(2500)
  const [manualProtein, setManualProtein] = useState<number | string>(150)
  const [manualCarbs, setManualCarbs] = useState<number | string>(280)
  const [manualFat, setManualFat] = useState<number | string>(75)
  const [manualRationale, setManualRationale] = useState('')

  // Estimate state
  const [estWeight, setEstWeight] = useState<number | string>(profile?.body_weight_kg || 80)
  const [estHeight, setEstHeight] = useState<number | string>(profile?.height_cm || 180)
  const [estAge, setEstAge] = useState<number | string>(25)
  const [estSex, setEstSex] = useState(profile?.sex_for_estimate || 'unspecified')
  const [estActivity, setEstActivity] = useState(profile?.activity_level || 'moderate')
  const [estGoal, setEstGoal] = useState(profile?.goal || 'build_strength')
  const [estimateResult, setEstimateResult] = useState<any | null>(null)

  // Preferences state
  const [allergies, setAllergies] = useState<string[]>([])
  const [dietTags, setDietTags] = useState<string[]>([])
  const [excludedIngredients, setExcludedIngredients] = useState<string[]>([])
  const [newExcludedInput, setNewExcludedInput] = useState('')
  const [cuisinePrefs, setCuisinePrefs] = useState<Record<string, string>>({})

  // Feedback states
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    if (isNutritionPaused || !isAdultConfirmed) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setErrorMessage(null)
    try {
      const [goal, prefs] = await Promise.all([
        api.getActiveNutritionGoal(),
        api.getNutritionPreferences(),
      ])
      setActiveGoal(goal)
      if (goal) {
        setManualKcal(goal.calorie_target_kcal || 2500)
        setManualProtein(goal.protein_target_g || 150)
        setManualCarbs(goal.carbs_target_g || 280)
        setManualFat(goal.fat_target_g || 75)
        setManualRationale(goal.rationale || '')
      }
      setAllergies(prefs.allergies || [])
      setDietTags(prefs.diet_tags || [])
      setExcludedIngredients(prefs.excluded_ingredients || [])
      setCuisinePrefs(prefs.cuisine_preferences || {})
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setErrorMessage(err.message)
      } else {
        console.warn('Could not load nutrition data:', err)
      }
    } finally {
      setIsLoading(false)
    }
  }, [isNutritionPaused, isAdultConfirmed])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Handle Manual Target Save (AC-22, AC-23)
  const handleSaveManualTarget = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      const saved = await api.createNutritionGoal({
        calorie_target_kcal: Number(manualKcal),
        protein_target_g: Number(manualProtein),
        carbs_target_g: Number(manualCarbs),
        fat_target_g: Number(manualFat),
        rationale: manualRationale.trim() || undefined,
      })
      setActiveGoal(saved)
      setSuccessMessage('Nutrition targets saved and versioned successfully.')
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not save nutrition target.')
    } finally {
      setIsSaving(false)
    }
  }

  // Handle Run Estimate (AC-18, AC-19, AC-20, AC-21)
  const handleRunEstimate = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setErrorMessage(null)
    setSuccessMessage(null)
    setEstimateResult(null)

    try {
      const est = await api.estimateNutrition({
        weight_kg: Number(estWeight),
        height_cm: Number(estHeight),
        age: Number(estAge),
        sex_for_estimate: estSex,
        activity_level: estActivity,
        goal: estGoal,
        save_as_active: false,
      })
      setEstimateResult(est)
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setErrorMessage(err.message)
      } else {
        setErrorMessage(err.message || 'Could not calculate target estimate.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  // Apply Estimate as Active Target
  const handleApplyEstimate = async () => {
    if (!estimateResult || estimateResult.status !== 'ok') return
    setIsSaving(true)
    try {
      const saved = await api.createNutritionGoal({
        calorie_target_kcal: estimateResult.calories,
        protein_target_g: estimateResult.protein_g,
        carbs_target_g: estimateResult.carbs_g,
        fat_target_g: estimateResult.fat_g,
        rationale: 'Mifflin-St Jeor estimate applied',
      })
      setActiveGoal(saved)
      setManualKcal(saved.calorie_target_kcal)
      setManualProtein(saved.protein_target_g)
      setManualCarbs(saved.carbs_target_g)
      setManualFat(saved.fat_target_g)
      setActiveTab('targets')
      setSuccessMessage('Estimated targets applied as your active targets.')
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not apply estimate.')
    } finally {
      setIsSaving(false)
    }
  }

  // Handle Preferences Save (S9, AC-57–61)
  const handleSavePreferences = async () => {
    setIsSaving(true)
    setErrorMessage(null)
    setSuccessMessage(null)
    try {
      await api.updateNutritionPreferences({
        allergies,
        diet_tags: dietTags,
        excluded_ingredients: excludedIngredients,
        cuisine_preferences: cuisinePrefs,
      })
      setSuccessMessage('Dietary preferences and allergen filters saved.')
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not save preferences.')
    } finally {
      setIsSaving(false)
    }
  }

  // Paused safeguard view (S7, AC-25)
  if (isNutritionPaused) {
    return (
      <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--accent-amber)', textAlign: 'center', padding: '2.5rem' }}>
          <Heart size={44} style={{ color: 'var(--accent-amber)', margin: '0 auto 1rem' }} />
          <h2>Nutrition Features Are Currently Paused</h2>
          <p style={{ marginTop: '0.5rem', maxWidth: '480px', marginInline: 'auto' }}>
            In accordance with Rule S7, nutrition planning and energy displays are currently switched off. All your training and workout features remain fully functional.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginTop: '1.5rem' }}
            onClick={async () => {
              await api.updateProfile({ nutrition_paused: false })
              await refreshProfile()
              loadData()
            }}
          >
            Resume Nutrition Features
          </button>
        </div>
      </div>
    )
  }

  // Adult confirmation safeguard view (S2, AC-17)
  if (!isAdultConfirmed) {
    return (
      <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)', textAlign: 'center', padding: '2.5rem' }}>
          <Shield size={44} style={{ color: 'var(--accent-primary)', margin: '0 auto 1rem' }} />
          <h2>Age Confirmation Required (Rule S2)</h2>
          <p style={{ marginTop: '0.5rem', maxWidth: '520px', marginInline: 'auto' }}>
            Nutrition targets, calorie estimates, and diet plan generation require confirming that you are 18 years or older. Workout logging remains available regardless.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: '1.5rem' }}
            onClick={async () => {
              await confirmAdult()
              loadData()
            }}
          >
            <Check size={18} />
            <span>I confirm I am 18 years or older</span>
          </button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div style={{ maxWidth: '900px', margin: '2rem auto', padding: '1.5rem 1rem', textAlign: 'center' }}>
        <div className="card" style={{ padding: '3rem 2rem' }}>
          <div className="skeleton" style={{ height: '32px', width: '250px', margin: '0 auto 1.5rem', borderRadius: '2px' }} />
          <div className="skeleton" style={{ height: '180px', width: '100%', borderRadius: 'var(--radius-sm)' }} />
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Utensils style={{ color: 'var(--accent-primary)' }} />
            Nutrition & Targets
          </h1>
          <p style={{ marginTop: '0.25rem' }}>Versioned nutritional targets, transparent estimates, and allergen filters</p>
        </div>

        {/* Tab switcher */}
        <div style={{ display: 'flex', background: 'var(--bg-surface-elevated)', padding: '0.25rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'targets' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab('targets')}
          >
            Active Targets
          </button>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'estimate' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab('estimate')}
          >
            <Calculator size={14} />
            <span>Estimate (S4)</span>
          </button>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'preferences' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab('preferences')}
          >
            <Sliders size={14} />
            <span>Preferences & Safety</span>
          </button>
        </div>
      </div>

      {successMessage && (
        <div style={{ background: 'var(--accent-emerald-bg)', border: '1px solid var(--accent-emerald-border)', color: 'var(--accent-emerald)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="status">
          <Check size={18} />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* TAB 1: ACTIVE TARGETS */}
      {activeTab === 'targets' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Active Target Banner */}
          <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)' }}>Current Active Target (AC-23)</h2>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Effective from {activeGoal?.effective_from || 'today'}
                </span>
              </div>
              {activeGoal?.warning && !isCaloriesHidden && (
                <span className="badge badge-amber">
                  {activeGoal.warning === 'below_recommended_minimum' ? 'Below Recommended Minimum (< 1500 kcal)' : activeGoal.warning}
                </span>
              )}
            </div>

            {/* Macro Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginTop: '0.5rem' }}>
              {!isCaloriesHidden && (
                <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Daily Energy</span>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-primary)', marginTop: '0.25rem' }}>
                    {activeGoal?.calorie_target_kcal || '—'} <span style={{ fontSize: '0.875rem' }}>kcal</span>
                  </div>
                </div>
              )}

              <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Protein Target</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.25rem' }}>
                  {activeGoal?.protein_target_g || '—'} <span style={{ fontSize: '0.875rem' }}>g</span>
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Carbohydrate Target</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.25rem' }}>
                  {activeGoal?.carbs_target_g || '—'} <span style={{ fontSize: '0.875rem' }}>g</span>
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Fat Target</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.25rem' }}>
                  {activeGoal?.fat_target_g || '—'} <span style={{ fontSize: '0.875rem' }}>g</span>
                </div>
              </div>
            </div>

            {isCaloriesHidden && (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.75rem', fontStyle: 'italic' }}>
                Energy numbers are hidden per your wellbeing preferences.
              </p>
            )}
          </div>

          {/* Edit / Create Target Form */}
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', marginBottom: '1rem', color: 'var(--text-main)' }}>
              Set New Target (Creates Versioned Goal)
            </h2>

            <form onSubmit={handleSaveManualTarget}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                {!isCaloriesHidden && (
                  <div className="form-group">
                    <label className="form-label" htmlFor="manual-kcal">Target Calories (kcal) *</label>
                    <input
                      id="manual-kcal"
                      type="number"
                      className="form-input"
                      min="500"
                      max="10000"
                      value={manualKcal}
                      onChange={(e) => setManualKcal(e.target.value)}
                      required
                    />
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label" htmlFor="manual-protein">Protein (grams) *</label>
                  <input
                    id="manual-protein"
                    type="number"
                    className="form-input"
                    min="10"
                    max="500"
                    value={manualProtein}
                    onChange={(e) => setManualProtein(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="manual-carbs">Carbohydrates (grams)</label>
                  <input
                    id="manual-carbs"
                    type="number"
                    className="form-input"
                    min="0"
                    max="1000"
                    value={manualCarbs}
                    onChange={(e) => setManualCarbs(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="manual-fat">Fat (grams)</label>
                  <input
                    id="manual-fat"
                    type="number"
                    className="form-input"
                    min="0"
                    max="500"
                    value={manualFat}
                    onChange={(e) => setManualFat(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="manual-rationale">Rationale / Context (Optional)</label>
                <input
                  id="manual-rationale"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Prescribed targets for strength phase"
                  value={manualRationale}
                  onChange={(e) => setManualRationale(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSaving}
                >
                  {isSaving ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : null}
                  <span>Save Versioned Target</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: ESTIMATE CALCULATOR (S4, AC-19–21) */}
      {activeTab === 'estimate' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Mifflin–St Jeor Energy Estimator (Rule S4)
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              Calculates BMR, TDEE, and recommended macro targets based on the validated Mifflin–St Jeor formula and standard athletic assumptions.
            </p>

            <form onSubmit={handleRunEstimate}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="est-weight">Body Weight (kg) *</label>
                  <input
                    id="est-weight"
                    type="number"
                    step="0.1"
                    className="form-input"
                    min="20"
                    max="400"
                    value={estWeight}
                    onChange={(e) => setEstWeight(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="est-height">Height (cm) *</label>
                  <input
                    id="est-height"
                    type="number"
                    step="0.5"
                    className="form-input"
                    min="50"
                    max="260"
                    value={estHeight}
                    onChange={(e) => setEstHeight(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="est-age">Age (years) *</label>
                  <input
                    id="est-age"
                    type="number"
                    className="form-input"
                    min="18"
                    max="120"
                    value={estAge}
                    onChange={(e) => setEstAge(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="est-sex">Sex Factor (Formula parameter s)</label>
                  <select
                    id="est-sex"
                    className="form-select"
                    value={estSex}
                    onChange={(e) => setEstSex(e.target.value)}
                  >
                    <option value="male">Male (s = +5)</option>
                    <option value="female">Female (s = −161)</option>
                    <option value="unspecified">Unspecified Midpoint (s = −78, AC-20)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="est-act">Activity Level</label>
                  <select
                    id="est-act"
                    className="form-select"
                    value={estActivity}
                    onChange={(e) => setEstActivity(e.target.value)}
                  >
                    <option value="sedentary">Sedentary (1.2×)</option>
                    <option value="light">Lightly Active (1.375×)</option>
                    <option value="moderate">Moderately Active (1.55×)</option>
                    <option value="very_active">Very Active (1.725×)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="est-goal">Goal Adjustment (Rule S6: No Deficits)</label>
                  <select
                    id="est-goal"
                    className="form-select"
                    value={estGoal}
                    onChange={(e) => setEstGoal(e.target.value)}
                  >
                    <option value="build_strength">Build Strength (+5% surplus)</option>
                    <option value="build_muscle">Build Muscle (+10% surplus)</option>
                    <option value="maintain">Maintain Current Weight (0%)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSaving}
                >
                  {isSaving ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : <Calculator size={16} />}
                  <span>Calculate Transparent Estimate</span>
                </button>
              </div>
            </form>
          </div>

          {/* Estimate Result Display */}
          {estimateResult && (
            <div className="card" style={{ borderLeft: estimateResult.status === 'ok' ? '4px solid var(--accent-emerald)' : '4px solid var(--accent-amber)' }}>
              {estimateResult.status === 'estimate_below_floor' ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-amber)', marginBottom: '0.5rem' }}>
                    <AlertCircle size={20} />
                    <h2 style={{ fontSize: '1.15rem' }}>Safety Notice: Energy Below Floor (Rule S5, AC-21)</h2>
                  </div>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    {estimateResult.warning}
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)' }}>Calculation Breakdown & Assumptions</h2>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={handleApplyEstimate}
                      disabled={isSaving}
                    >
                      <Check size={14} />
                      <span>Apply as Active Targets</span>
                    </button>
                  </div>

                  {/* Numbers */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                    {!isCaloriesHidden && (
                      <div style={{ background: 'var(--bg-surface)', padding: '0.875rem', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Calories</span>
                        <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>
                          {estimateResult.calories} kcal
                        </div>
                      </div>
                    )}

                    <div style={{ background: 'var(--bg-surface)', padding: '0.875rem', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Protein (1.6 g/kg)</span>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        {estimateResult.protein_g} g
                      </div>
                    </div>

                    <div style={{ background: 'var(--bg-surface)', padding: '0.875rem', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Carbs (Remainder)</span>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        {estimateResult.carbs_g} g
                      </div>
                    </div>

                    <div style={{ background: 'var(--bg-surface)', padding: '0.875rem', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{isCaloriesHidden ? 'Fat' : 'Fat (25% kcal)'}</span>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-main)' }}>
                        {estimateResult.fat_g} g
                      </div>
                    </div>
                  </div>

                  {/* Formula and transparency assumptions (Rule S4, AC-19) */}
                  <div style={{ background: 'var(--bg-surface)', padding: '0.875rem', borderRadius: 'var(--radius-sm)', fontSize: '0.8125rem' }}>
                    <div style={{ color: 'var(--text-main)', fontWeight: 600, marginBottom: '0.25rem' }}>
                      Formula: {estimateResult.formula}
                    </div>
                    {!isCaloriesHidden && <div style={{ color: 'var(--text-dim)' }}>
                      BMR: <strong>{estimateResult.bmr} kcal</strong> • TDEE Multiplier: <strong>{estimateResult.activity_factor}</strong> • Goal Factor: <strong>{estimateResult.goal_adjustment}</strong>
                    </div>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PREFERENCES & ALLERGEN FILTERS (S9, AC-57–61) */}
      {activeTab === 'preferences' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Allergens Hard Filters (S9, AC-57) */}
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '0.35rem' }}>
              Allergens (Hard Safety Filters — Rule S9)
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Ingredients carrying selected allergens will be strictly excluded from all generated plans and substitutions.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
              {EU_ALLERGENS.map((allergen) => {
                const checked = allergies.includes(allergen)
                return (
                  <label
                    key={allergen}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      background: checked ? 'var(--accent-rose-bg)' : 'var(--bg-surface)',
                      border: checked ? '1px solid var(--accent-rose-border)' : '1px solid var(--border-subtle)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setAllergies([...allergies, allergen])
                        } else {
                          setAllergies(allergies.filter((a) => a !== allergen))
                        }
                      }}
                      style={{ accentColor: 'var(--accent-rose)' }}
                    />
                    <span style={{ fontSize: '0.8125rem', color: checked ? 'var(--text-main)' : 'var(--text-muted)', textTransform: 'capitalize' }}>
                      {allergen.replace('_', ' ')}
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          {/* Diet Tags (AC-59) */}
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '0.35rem' }}>
              Dietary Restrictions (AC-59)
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Only recipes carrying your selected diet tags will be considered candidates.
            </p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {DIET_TAGS.map((tag) => {
                const checked = dietTags.includes(tag)
                return (
                  <button
                    key={tag}
                    type="button"
                    className={`btn btn-sm ${checked ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => {
                      if (checked) {
                        setDietTags(dietTags.filter((t) => t !== tag))
                      } else {
                        setDietTags([...dietTags, tag])
                      }
                    }}
                  >
                    {checked ? <Check size={14} /> : null}
                    <span style={{ textTransform: 'capitalize' }}>{tag.replace('_', ' ')}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Excluded Ingredients (AC-59) */}
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '0.35rem' }}>
              Excluded Ingredients (AC-59)
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Any recipe containing these ingredients will never appear in your plans.
            </p>

            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Cilantro, Mushrooms, Onion..."
                value={newExcludedInput}
                onChange={(e) => setNewExcludedInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    if (newExcludedInput.trim()) {
                      setExcludedIngredients([...excludedIngredients, newExcludedInput.trim()])
                      setNewExcludedInput('')
                    }
                  }
                }}
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  if (newExcludedInput.trim()) {
                    setExcludedIngredients([...excludedIngredients, newExcludedInput.trim()])
                    setNewExcludedInput('')
                  }
                }}
              >
                Add
              </button>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {excludedIngredients.map((ing, idx) => (
                <span
                  key={idx}
                  className="badge badge-amber"
                  style={{ padding: '0.35rem 0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <span>{ing}</span>
                  <button
                    type="button"
                    onClick={() => setExcludedIngredients(excludedIngredients.filter((_, i) => i !== idx))}
                    style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0 }}
                    aria-label={`Remove ${ing}`}
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Cuisines (AC-61) */}
          <div className="card">
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', marginBottom: '0.35rem' }}>
              Cuisine Preferences (AC-61)
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Preferred cuisines are prioritized during plan generation.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
              {CUISINES.map((c) => {
                const currentPref = cuisinePrefs[c] || 'neutral'
                return (
                  <div key={c} style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-main)', textTransform: 'capitalize', marginBottom: '0.35rem' }}>
                      {c.replace('_', ' ')}
                    </div>
                    <select
                      className="form-select"
                      style={{ padding: '0.25rem 0.5rem', minHeight: '34px' }}
                      value={currentPref}
                      onChange={(e) => {
                        setCuisinePrefs({ ...cuisinePrefs, [c]: e.target.value })
                      }}
                    >
                      <option value="preferred">Preferred (+1.0)</option>
                      <option value="like">Like (+0.5)</option>
                      <option value="neutral">Neutral (0.0)</option>
                      <option value="avoid">Avoid (−1.0)</option>
                    </select>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Submit preferences */}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSavePreferences}
              disabled={isSaving}
            >
              {isSaving ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : null}
              <span>Save Preferences</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
