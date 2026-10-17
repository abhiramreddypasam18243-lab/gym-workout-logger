import React, { useState, useEffect, useId } from 'react'
import {
  Activity,
  Award,
  Calendar,
  PlusCircle,
  TrendingUp,
  AlertCircle,
  Info,
  CheckCircle,
  Clock,
  Sparkles,
  RefreshCw,
  Trash2,
  UtensilsCrossed,
  ShieldCheck,
  Dumbbell,
} from 'lucide-react'
import { apiClient } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { kgToLb } from '../utils/units'

export const Dashboard: React.FC<{
  onNavigateToLogger?: () => void
  onNavigateToMealPlan?: () => void
}> = ({ onNavigateToLogger, onNavigateToMealPlan }) => {
  const { profile, units } = useAuth()
  const formId = useId()

  const [dashboardData, setDashboardData] = useState<any>(null)
  const [insightsData, setInsightsData] = useState<any>(null)
  const [analyticsData, setAnalyticsData] = useState<any>(null)
  const [recentLogs, setRecentLogs] = useState<any[]>([])
  const [foodsList, setFoodsList] = useState<any[]>([])
  const [recipesList, setRecipesList] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Intake Logger Modal State
  const [showLogModal, setShowLogModal] = useState<boolean>(false)
  const [logType, setLogType] = useState<'food' | 'recipe'>('food')
  const [selectedItemId, setSelectedItemId] = useState<string>('')
  const [mealType, setMealType] = useState<string>('lunch')
  const [quantity, setQuantity] = useState<string>('100')
  const [unit, setUnit] = useState<string>('g')
  const [consumedAt, setConsumedAt] = useState<string>(
    new Date().toISOString().slice(0, 16)
  )
  const [notes, setNotes] = useState<string>('')
  const [isSubmittingLog, setIsSubmittingLog] = useState<boolean>(false)
  const [logSuccessMessage, setLogSuccessMessage] = useState<string | null>(null)

  const loadData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const today = new Date().toISOString().split('T')[0]
      const sevenDaysAgo = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0]

      const [dash, insights, analytics, logs, foods, recipes] = await Promise.all([
        apiClient.getDashboard(),
        apiClient.getInsights(5),
        apiClient.getNutritionAnalytics(sevenDaysAgo, today),
        apiClient.listNutritionLogs(sevenDaysAgo, today),
        apiClient.searchFoods({ page: 1, page_size: 100 }),
        apiClient.listRecipes({ page: 1, page_size: 100 }),
      ])

      setDashboardData(dash)
      setInsightsData(insights)
      setAnalyticsData(analytics)
      setRecentLogs(logs)
      setFoodsList(foods.items || [])
      setRecipesList(recipes.items || [])

      if (foods.items && foods.items.length > 0) {
        setSelectedItemId(foods.items[0].id)
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard data.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreateLog = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedItemId || !quantity || Number(quantity) <= 0) {
      alert('Please select an item and enter a valid quantity.')
      return
    }

    setIsSubmittingLog(true)
    try {
      const itemPayload =
        logType === 'food'
          ? {
              food_id: selectedItemId,
              quantity: Number(quantity),
              unit,
            }
          : {
              recipe_id: selectedItemId,
              quantity: Number(quantity),
              unit,
            }

      await apiClient.createNutritionLog({
        consumed_at: new Date(consumedAt).toISOString(),
        meal_type: mealType,
        notes: notes.trim() || undefined,
        items: [itemPayload],
      })

      setLogSuccessMessage('Intake logged successfully with snapshot!')
      setTimeout(() => setLogSuccessMessage(null), 3500)
      setShowLogModal(false)
      setNotes('')
      // Reload dashboard and analytics
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to record intake log.')
    } finally {
      setIsSubmittingLog(false)
    }
  }

  const handleDeleteLog = async (logId: string) => {
    if (!window.confirm('Delete this logged meal?')) return
    try {
      await apiClient.deleteNutritionLog(logId)
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to delete log.')
    }
  }

  const formatVolume = (volKg: number) => {
    if (units === 'lb') {
      return `${Math.round(kgToLb(volKg)).toLocaleString()} lb`
    }
    return `${Math.round(volKg).toLocaleString()} kg`
  }

  const getNeutralBadgeStyle = (label: string) => {
    switch (label) {
      case 'Within target range':
        return {
          background: 'rgba(16, 185, 129, 0.15)',
          color: '#10b981',
          border: '1px solid rgba(16, 185, 129, 0.3)',
        }
      case 'Above target':
        return {
          background: 'rgba(245, 158, 11, 0.15)',
          color: '#f59e0b',
          border: '1px solid rgba(245, 158, 11, 0.3)',
        }
      case 'Below target':
        return {
          background: 'rgba(56, 189, 248, 0.15)',
          color: '#38bdf8',
          border: '1px solid rgba(56, 189, 248, 0.3)',
        }
      default:
        return {
          background: 'rgba(100, 116, 139, 0.15)',
          color: '#94a3b8',
          border: '1px solid rgba(100, 116, 139, 0.3)',
        }
    }
  }

  if (isLoading && !dashboardData) {
    return (
      <div style={{ padding: '3rem 1rem', display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh', flexDirection: 'column', gap: '1rem' }}>
        <div className="spinner" style={{ width: '40px', height: '40px' }} />
        <p style={{ color: 'var(--text-dim)', fontSize: '0.875rem' }}>Loading Titan Dashboard & Insights...</p>
      </div>
    )
  }

  const workoutCount = dashboardData?.weekly_workout_count || 0
  const workoutTarget = dashboardData?.weekly_session_target || profile?.weekly_session_target || 4
  const workoutProgressPct = Math.min(100, Math.round((workoutCount / (workoutTarget || 1)) * 100))
  const volumeKg = dashboardData?.weekly_volume_kg || 0
  const prCount = dashboardData?.weekly_pr_count || 0
  const loggedDaysCount = dashboardData?.logged_days_count || 0
  const adherencePct = dashboardData?.weekly_adherence_percentage ?? 0
  const avgProtein = dashboardData?.avg_daily_protein_g ?? 0
  const targetProtein = dashboardData?.target_daily_protein_g ?? 0
  const avgCalories = dashboardData?.avg_daily_calories_kcal ?? 0
  const targetCalories = dashboardData?.target_daily_calories_kcal ?? 0
  const isCaloriesHidden = profile?.calories_hidden || false

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Top Header / Actions Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Titan Performance <span style={{ color: 'var(--accent-primary)' }}>Dashboard</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Unified training load, weekly adherence, and non-causal performance correlations.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {onNavigateToLogger && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onNavigateToLogger}
              id="dash-start-workout-btn"
            >
              <Dumbbell size={15} />
              <span>Start Workout</span>
            </button>
          )}

          {onNavigateToMealPlan && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onNavigateToMealPlan}
              id="dash-view-mealplan-btn"
            >
              <UtensilsCrossed size={15} />
              <span>Active Plan</span>
            </button>
          )}

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadData}
            title="Refresh metrics"
            id="refresh-dashboard-btn"
          >
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setShowLogModal(true)}
            id="quick-log-intake-btn"
          >
            <PlusCircle size={16} />
            <span>Log Meal Intake</span>
          </button>
        </div>
      </div>

      {logSuccessMessage && (
        <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 'var(--radius-md)', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle size={18} />
          <span>{logSuccessMessage}</span>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: 'var(--radius-md)', color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Grid of Key Weekly Metrics (AC-85) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {/* Metric 1: Weekly Workouts */}
        <div className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Workouts This Week
            </span>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
              <Activity size={18} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
              <span style={{ fontSize: '1.875rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {workoutCount}
              </span>
              <span style={{ color: 'var(--text-dim)', fontSize: '0.9375rem' }}>
                / {workoutTarget} target
              </span>
            </div>
            {/* Progress bar */}
            <div style={{ width: '100%', height: '6px', background: 'var(--border-subtle)', borderRadius: '3px', marginTop: '0.5rem', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${workoutProgressPct}%`,
                  height: '100%',
                  background: workoutCount >= workoutTarget ? '#10b981' : 'var(--accent-primary)',
                  borderRadius: '3px',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
          </div>
        </div>

        {/* Metric 2: Weekly Volume Lifted (AC-85b) */}
        <div className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Weekly Volume Lifted
            </span>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
              <TrendingUp size={18} />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '1.875rem', fontWeight: 800, color: 'var(--text-main)' }}>
              {formatVolume(volumeKg)}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
              Total work completed across all sets
            </p>
          </div>
        </div>

        {/* Metric 3: Personal Records Set (AC-85c) */}
        <div className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Personal Records
            </span>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f59e0b' }}>
              <Award size={18} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
              <span style={{ fontSize: '1.875rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {prCount}
              </span>
              <span style={{ color: 'var(--text-dim)', fontSize: '0.875rem' }}>
                PRs unlocked this week
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
              Top 1RM calculations & load milestones
            </p>
          </div>
        </div>

        {/* Metric 4: Weekly Nutrition Adherence (AC-85d, e, f, AC-84) */}
        <div className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Nutrition Adherence
            </span>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(168, 85, 247, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#c084fc' }}>
              <ShieldCheck size={18} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
              <span style={{ fontSize: '1.875rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {loggedDaysCount > 0 ? `${Math.round(adherencePct)}%` : '—'}
              </span>
              <span style={{ color: 'var(--text-dim)', fontSize: '0.8125rem' }}>
                ({loggedDaysCount} of 7 days logged)
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
              Within ±10% energy target. <span style={{ color: 'var(--text-muted)' }}>Unlogged days excluded (AC-84).</span>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Nutrition Overview Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {/* Protein Intake vs Target */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Avg Daily Protein (Logged Days)
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              Target: {targetProtein > 0 ? `${targetProtein}g` : '—'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
              {loggedDaysCount > 0 ? `${avgProtein}g` : 'No logs yet'}
            </span>
            {targetProtein > 0 && loggedDaysCount > 0 && (
              <span style={{ fontSize: '0.8125rem', color: avgProtein >= targetProtein ? '#10b981' : '#f59e0b' }}>
                {avgProtein >= targetProtein ? '✓ Meets target' : `(${targetProtein - avgProtein}g below)`}
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '0.375rem' }}>
            Calculated across {loggedDaysCount} active logging day{loggedDaysCount === 1 ? '' : 's'}.
          </div>
        </div>

        {/* Calories Intake vs Target (Conditional if not hidden) */}
        {!isCaloriesHidden ? (
          <div className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                Avg Daily Energy (Logged Days)
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                Target: {targetCalories > 0 ? `${targetCalories} kcal` : '—'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f59e0b' }}>
                {loggedDaysCount > 0 ? `${avgCalories} kcal` : 'No logs yet'}
              </span>
              {targetCalories > 0 && loggedDaysCount > 0 && (
                <span
                  style={{
                    fontSize: '0.8125rem',
                    color:
                      Math.abs(avgCalories - targetCalories) / targetCalories <= 0.1
                        ? '#10b981'
                        : '#f59e0b',
                  }}
                >
                  {Math.abs(avgCalories - targetCalories) / targetCalories <= 0.1
                    ? '✓ Within target range'
                    : avgCalories > targetCalories
                    ? 'Above target'
                    : 'Below target'}
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '0.375rem' }}>
              Target range: ±10% ({Math.round(targetCalories * 0.9)} - {Math.round(targetCalories * 1.1)} kcal).
            </div>
          </div>
        ) : (
          <div className="card" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Info size={24} style={{ color: 'var(--text-dim)' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-main)' }}>
                Calorie Display Hidden
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                Calorie numbers are concealed based on your profile privacy preference.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Daily Planned vs Logged Comparison (AC-83, AC-84) */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <UtensilsCrossed size={18} style={{ color: 'var(--accent-primary)' }} />
              Planned vs Logged Intake (Last 7 Days)
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
              Target range is ±10% of planned energy. Strictly neutral status terminology (AC-83).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
              Excludes unlogged days (AC-84)
            </span>
          </div>
        </div>

        {analyticsData?.days && analyticsData.days.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.625rem 0.5rem' }}>Date</th>
                  <th style={{ padding: '0.625rem 0.5rem' }}>Energy (Logged / Planned)</th>
                  <th style={{ padding: '0.625rem 0.5rem' }}>Protein (Logged / Planned)</th>
                  <th style={{ padding: '0.625rem 0.5rem' }}>Carbs</th>
                  <th style={{ padding: '0.625rem 0.5rem' }}>Fat</th>
                  <th style={{ padding: '0.625rem 0.5rem' }}>Neutral Status Label</th>
                </tr>
              </thead>
              <tbody>
                {analyticsData.days.map((d: any) => {
                  const hasLogs = d.logged_meals_count > 0
                  return (
                    <tr
                      key={d.date}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        background: hasLogs ? 'transparent' : 'rgba(15, 23, 42, 0.3)',
                      }}
                    >
                      <td style={{ padding: '0.625rem 0.5rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        {d.date}
                        {!hasLogs && (
                          <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', display: 'block' }}>
                            (Not logged)
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '0.625rem 0.5rem' }}>
                        {hasLogs ? (
                          isCaloriesHidden ? (
                            <span style={{ color: 'var(--text-dim)' }}>Hidden</span>
                          ) : (
                            <div>
                              <span>{d.comparison.logged_energy_kcal} / {d.comparison.planned_energy_kcal} kcal</span>
                              <span
                                style={{
                                  fontSize: '0.6875rem',
                                  marginLeft: '0.375rem',
                                  color: d.comparison.delta_energy_kcal >= 0 ? '#f59e0b' : '#38bdf8',
                                }}
                              >
                                ({d.comparison.delta_energy_kcal > 0 ? '+' : ''}{d.comparison.delta_energy_kcal} kcal, {d.comparison.delta_energy_percentage > 0 ? '+' : ''}{d.comparison.delta_energy_percentage}%)
                              </span>
                            </div>
                          )
                        ) : (
                          <span style={{ color: 'var(--text-dim)' }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '0.625rem 0.5rem' }}>
                        {hasLogs ? (
                          <div>
                            <span>{d.comparison.logged_protein_g}g / {d.comparison.planned_protein_g}g</span>
                            <span
                              style={{
                                fontSize: '0.6875rem',
                                marginLeft: '0.375rem',
                                color: d.comparison.delta_protein_g >= 0 ? '#10b981' : '#f43f5e',
                              }}
                            >
                              ({d.comparison.delta_protein_g > 0 ? '+' : ''}{d.comparison.delta_protein_g}g, {d.comparison.delta_protein_percentage > 0 ? '+' : ''}{d.comparison.delta_protein_percentage}%)
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-dim)' }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '0.625rem 0.5rem' }}>
                        {hasLogs ? `${d.comparison.logged_carbs_g}g` : '—'}
                      </td>
                      <td style={{ padding: '0.625rem 0.5rem' }}>
                        {hasLogs ? `${d.comparison.logged_fat_g}g` : '—'}
                      </td>
                      <td style={{ padding: '0.625rem 0.5rem' }}>
                        {hasLogs ? (
                          <span
                            style={{
                              padding: '0.2rem 0.5rem',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              ...getNeutralBadgeStyle(d.comparison.status_label),
                            }}
                          >
                            {d.comparison.status_label}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                            Excluded from average
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-dim)' }}>
            No planned meals or logs found in this period.
          </div>
        )}
      </div>

      {/* Non-Causal Descriptive Insights Panel (AC-86, AC-87) */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={18} style={{ color: 'var(--accent-primary)' }} />
              Observational Insights Engine
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
              Automated pattern detection with strictly non-causal language and mandatory limitations notes (AC-87).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.6875rem', padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.1)', color: 'var(--accent-primary)', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
              Rule S1 & AC-87 Compliant
            </span>
          </div>
        </div>

        {/* Progress toward unlocking insights (AC-86c) */}
        {!insightsData?.is_unlocked ? (
          <div style={{ padding: '1.25rem', background: 'rgba(15, 23, 42, 0.7)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
                <Clock size={16} />
              </div>
              <div>
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  Insights Progress Indicator (AC-86c)
                </h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {insightsData?.progress?.message || 'Minimum 5 workout sessions and 5 nutrition logging days required before insights unlock.'}
                </p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              {/* Workout Sessions Progress */}
              <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Workout Sessions</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                    {insightsData?.progress?.completed_sessions || 0} / {insightsData?.progress?.required_sessions || 5}
                  </span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'var(--border-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, (((insightsData?.progress?.completed_sessions || 0) / (insightsData?.progress?.required_sessions || 5)) * 100))}%`,
                      height: '100%',
                      background: 'var(--accent-primary)',
                      borderRadius: '3px',
                    }}
                  />
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                  {(insightsData?.progress?.sessions_needed || 0) > 0
                    ? `${insightsData.progress.sessions_needed} more session(s) needed`
                    : '✓ Session threshold reached'}
                </div>
              </div>

              {/* Nutrition Days Progress */}
              <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Nutrition Logged Days</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                    {insightsData?.progress?.completed_nutrition_days || 0} / {insightsData?.progress?.required_nutrition_days || 5}
                  </span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'var(--border-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, (((insightsData?.progress?.completed_nutrition_days || 0) / (insightsData?.progress?.required_nutrition_days || 5)) * 100))}%`,
                      height: '100%',
                      background: '#10b981',
                      borderRadius: '3px',
                    }}
                  />
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                  {(insightsData?.progress?.nutrition_days_needed || 0) > 0
                    ? `${insightsData.progress.nutrition_days_needed} more day(s) needed`
                    : '✓ Nutrition threshold reached'}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
            {/* Insight Cards (AC-86a, b, AC-87) */}
            {insightsData.insights?.map((ins: any, idx: number) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.6875rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--accent-primary)', letterSpacing: '0.05em' }}>
                      {ins.category.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
                      Window: {ins.window} (n={ins.sample_size})
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>
                    {ins.title}
                  </h3>

                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', lineHeight: '1.5', marginBottom: '0.75rem' }}>
                    {ins.observation}
                  </p>
                </div>

                {/* Explicit Limitations Box (AC-87) */}
                <div style={{ padding: '0.625rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent-primary)' }}>
                  <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Info size={12} style={{ color: 'var(--accent-primary)' }} />
                    Limitations Note (AC-87)
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
                    {ins.limitations}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Meal Intake Logs List (AC-82) */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Calendar size={18} style={{ color: 'var(--accent-primary)' }} />
              Recent Intake Logs (AC-82)
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
              Logged foods and recipes with captured historical nutrient snapshots.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowLogModal(true)}
          >
            <PlusCircle size={15} />
            <span>Add Log</span>
          </button>
        </div>

        {recentLogs && recentLogs.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {recentLogs.map((log: any) => (
              <div
                key={log.id}
                style={{
                  padding: '0.875rem',
                  background: 'rgba(15, 23, 42, 0.5)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
                    <UtensilsCrossed size={18} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-main)', textTransform: 'capitalize' }}>
                        {log.meal_type}
                      </span>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
                        {new Date(log.consumed_at).toLocaleString()}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
                      {log.items?.map((it: any, i: number) => (
                        <span key={it.id || i}>
                          {it.food?.name || it.recipe?.name || 'Custom item'} ({it.quantity}{it.unit})
                          {i < log.items.length - 1 ? ', ' : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  {/* Snapshot Macros */}
                  <div style={{ textAlign: 'right', fontSize: '0.75rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {log.items?.reduce((acc: number, it: any) => acc + (Number(it.nutrient_snapshot?.energy_kcal) || 0), 0)} kcal
                    </div>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.6875rem' }}>
                      P: {Math.round(log.items?.reduce((acc: number, it: any) => acc + (Number(it.nutrient_snapshot?.protein_g) || 0), 0))}g
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleDeleteLog(log.id)}
                    title="Delete meal log"
                    style={{ color: '#f43f5e', padding: '0.375rem' }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-dim)' }}>
            No intake logs recorded yet for this period. Click "Log Meal Intake" to start.
          </div>
        )}
      </div>

      {/* Intake Logging Modal (AC-82) */}
      {showLogModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={`${formId}-title`}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem',
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '500px',
              width: '100%',
              padding: '1.5rem',
              maxHeight: '90vh',
              overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2 id={`${formId}-title`} style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <PlusCircle size={20} style={{ color: 'var(--accent-primary)' }} />
                Log Meal Intake (AC-82)
              </h2>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowLogModal(false)}
                style={{ padding: '0.25rem 0.5rem' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateLog} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Type Switcher: Food vs Recipe */}
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}>
                  Log Item Type
                </label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className={`btn btn-sm ${logType === 'food' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ flex: 1 }}
                    onClick={() => {
                      setLogType('food')
                      if (foodsList.length > 0) setSelectedItemId(foodsList[0].id)
                      setUnit('g')
                    }}
                  >
                    Single Food Item
                  </button>
                  <button
                    type="button"
                    className={`btn btn-sm ${logType === 'recipe' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ flex: 1 }}
                    onClick={() => {
                      setLogType('recipe')
                      if (recipesList.length > 0) setSelectedItemId(recipesList[0].id)
                      setUnit('serving')
                    }}
                  >
                    Recipe
                  </button>
                </div>
              </div>

              {/* Item Selector */}
              <div>
                <label
                  htmlFor={`${formId}-item`}
                  style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}
                >
                  {logType === 'food' ? 'Select Food' : 'Select Recipe'}
                </label>
                <select
                  id={`${formId}-item`}
                  className="input"
                  value={selectedItemId}
                  onChange={(e) => setSelectedItemId(e.target.value)}
                  style={{ width: '100%' }}
                  required
                >
                  {logType === 'food' ? (
                    foodsList.map((f: any) => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.brand || 'Common'}) — {f.serving_size_g}g serving
                      </option>
                    ))
                  ) : (
                    recipesList.map((r: any) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.servings_yield} servings yield)
                      </option>
                    ))
                  )}
                </select>
              </div>

              {/* Meal Type & Consumed At */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label
                    htmlFor={`${formId}-meal-type`}
                    style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}
                  >
                    Meal Type
                  </label>
                  <select
                    id={`${formId}-meal-type`}
                    className="input"
                    value={mealType}
                    onChange={(e) => setMealType(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="breakfast">Breakfast</option>
                    <option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option>
                    <option value="snack">Snack</option>
                  </select>
                </div>

                <div>
                  <label
                    htmlFor={`${formId}-consumed-at`}
                    style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}
                  >
                    Consumed At
                  </label>
                  <input
                    id={`${formId}-consumed-at`}
                    type="datetime-local"
                    className="input"
                    value={consumedAt}
                    onChange={(e) => setConsumedAt(e.target.value)}
                    style={{ width: '100%' }}
                    required
                  />
                </div>
              </div>

              {/* Quantity & Unit */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label
                    htmlFor={`${formId}-quantity`}
                    style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}
                  >
                    Quantity
                  </label>
                  <input
                    id={`${formId}-quantity`}
                    type="number"
                    step="any"
                    min="0.1"
                    className="input"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    style={{ width: '100%' }}
                    required
                  />
                </div>

                <div>
                  <label
                    htmlFor={`${formId}-unit`}
                    style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}
                  >
                    Unit (AC-82)
                  </label>
                  <select
                    id={`${formId}-unit`}
                    className="input"
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="g">Grams (g)</option>
                    <option value="ml">Milliliters (ml)</option>
                    <option value="oz">Ounces (oz)</option>
                    <option value="serving">Serving</option>
                  </select>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label
                  htmlFor={`${formId}-notes`}
                  style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}
                >
                  Notes (Optional)
                </label>
                <input
                  id={`${formId}-notes`}
                  type="text"
                  placeholder="e.g. Post-workout meal"
                  className="input"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Snapshot Notice (AC-82) */}
              <div style={{ padding: '0.5rem 0.75rem', background: 'rgba(56, 189, 248, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(56, 189, 248, 0.2)', fontSize: '0.6875rem', color: 'var(--accent-primary)' }}>
                ℹ Historical nutrient snapshot will be permanently bound to this log to preserve historical reporting accuracy even if catalogue data changes.
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowLogModal(false)}
                  disabled={isSubmittingLog}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmittingLog}
                >
                  {isSubmittingLog ? 'Saving...' : 'Record Intake'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
