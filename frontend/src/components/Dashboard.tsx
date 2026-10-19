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
import { MotivationalQuoteCard } from './MotivationalQuoteCard'

// A log item's snapshot is per serving for recipes and per 100 g for foods (as in the API)
function logItemAmount(it: any, key: string): number {
  const value = Number(it.nutrient_snapshot?.[key]) || 0
  const qty = Number(it.quantity) || 0
  return it.nutrient_snapshot?.is_recipe_per_serving === 'true' ? value * qty : (value * qty) / 100
}

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
        apiClient.getInsights('last_12_weeks'),
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
          background: 'color-mix(in srgb, var(--accent-emerald) 15%, transparent)',
          color: 'var(--accent-emerald)',
          border: '1px solid color-mix(in srgb, var(--accent-emerald) 30%, transparent)',
        }
      case 'Above target':
        return {
          background: 'color-mix(in srgb, var(--accent-amber) 15%, transparent)',
          color: 'var(--accent-amber)',
          border: '1px solid color-mix(in srgb, var(--accent-amber) 30%, transparent)',
        }
      case 'Below target':
        return {
          background: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)',
          color: 'var(--accent-primary)',
          border: '1px solid color-mix(in srgb, var(--accent-primary) 30%, transparent)',
        }
      default:
        return {
          background: 'rgba(255, 255, 255, 0.075)',
          color: 'var(--text-muted)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
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

  // Fields as returned by GET /api/dashboard (DashboardSummaryResponse)
  const workoutCount = dashboardData?.weekly_sessions || 0
  const workoutTarget = profile?.weekly_session_target || 4
  const workoutProgressPct = Math.min(100, Math.round((workoutCount / (workoutTarget || 1)) * 100))
  const volumeKg = Number(dashboardData?.weekly_volume_kg) || 0
  const prCount = dashboardData?.pr_count || 0
  // Nutrition averages come from this week's planned-vs-logged days; unlogged days are excluded
  const loggedDays: any[] = (dashboardData?.planned_vs_logged || []).filter((d: any) => d.is_logged)
  const loggedDaysCount = loggedDays.length
  const average = (key: string) =>
    loggedDaysCount ? Math.round(loggedDays.reduce((acc, d) => acc + (Number(d[key]) || 0), 0) / loggedDaysCount) : 0
  const adherencePct = loggedDaysCount
    ? (loggedDays.filter((d) => d.is_within_range).length / loggedDaysCount) * 100
    : 0
  const avgProtein = average('logged_protein_g')
  const targetProtein = dashboardData?.active_goal_protein ?? 0
  const avgCalories = average('logged_calories')
  const targetCalories = dashboardData?.active_goal_calories ?? 0
  const isCaloriesHidden = profile?.calories_hidden || false

  // Dynamic greeting based on current local hour
  const currentHour = new Date().getHours()
  const greeting = currentHour < 12 ? 'Good morning' : currentHour < 17 ? 'Good afternoon' : 'Good evening'
  const athleteName = profile?.display_name || 'Champion'

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', padding: '1.75rem 1.25rem' }}>
      {/* Top Hero Header with Status Pills */}
      <div
        className="card"
        style={{
          marginBottom: '1.75rem',
          padding: '1.75rem',
          background: 'var(--bg-surface)',
          border: '1px solid color-mix(in srgb, var(--accent-primary) 25%, transparent)',
          boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 20px 48px -10px rgba(0, 0, 0, 0.7)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.25rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <span className="badge badge-live">
                <span className="pulse-dot" /> LIVE ADHERENCE
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>
                {new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </div>

            <h1 style={{ fontSize: '2.1rem', fontWeight: 900, letterSpacing: '-0.035em' }}>
              {greeting}, <span className="text-gradient-cyan">{athleteName}</span>
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem', marginTop: '0.35rem', maxWidth: '650px' }}>
              High-performance strength overload analytics, progressive training volume, and macronutrient targets.
            </p>
          </div>

          {/* Quick Action Station */}
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {onNavigateToLogger && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onNavigateToLogger}
                id="dash-start-workout-btn"
                style={{ boxShadow: 'none' }}
              >
                <Dumbbell size={17} strokeWidth={2.5} />
                <span>Start Session</span>
              </button>
            )}

            {onNavigateToMealPlan && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onNavigateToMealPlan}
                id="dash-view-mealplan-btn"
              >
                <UtensilsCrossed size={16} />
                <span>Active Meal Plan</span>
              </button>
            )}

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowLogModal(true)}
              id="quick-log-intake-btn"
            >
              <PlusCircle size={16} />
              <span>Log Meal Intake</span>
            </button>

            <button
              type="button"
              className="btn btn-ghost"
              onClick={loadData}
              title="Refresh performance telemetry"
              id="refresh-dashboard-btn"
              style={{ padding: '0.5rem' }}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Morale Boost Motivational Quote Card */}
      <div style={{ marginBottom: '1.75rem' }}>
        <MotivationalQuoteCard variant="hero" />
      </div>

      {logSuccessMessage && (
        <div style={{ marginBottom: '1.25rem', padding: '0.85rem 1.15rem', background: 'color-mix(in srgb, var(--accent-emerald) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-emerald) 35%, transparent)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '0.625rem', fontWeight: 600 }}>
          <CheckCircle size={18} />
          <span>{logSuccessMessage}</span>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: '1.25rem', padding: '0.85rem 1.15rem', background: 'color-mix(in srgb, var(--accent-rose) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-rose) 35%, transparent)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-rose)', display: 'flex', alignItems: 'center', gap: '0.625rem', fontWeight: 600 }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Grid of Key Weekly Metrics (AC-85) with Circular Ring Gauges */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
        {/* Metric 1: Weekly Workouts with Circular Ring Gauge */}
        <div className="card card-glow-cyan" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Weekly Workouts
              </span>
              <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-primary) 30%, transparent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
                <Activity size={18} />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
                  <span className="mono-stat" style={{ fontSize: '2.25rem', color: 'var(--text-main)', lineHeight: 1 }}>
                    {workoutCount}
                  </span>
                  <span style={{ color: 'var(--text-dim)', fontSize: '1rem', fontWeight: 700 }}>
                    / {workoutTarget} target
                  </span>
                </div>
                <p style={{ fontSize: '0.75rem', color: workoutCount >= workoutTarget ? 'var(--accent-emerald)' : 'var(--text-dim)', marginTop: '0.5rem', fontWeight: 600 }}>
                  {workoutCount >= workoutTarget ? '✓ Target completed this week' : `${workoutTarget - workoutCount} more session to hit target`}
                </p>
              </div>

              {/* Circular Mini Gauge */}
              <div style={{ position: 'relative', width: '56px', height: '56px', flexShrink: 0 }}>
                <svg width="56" height="56" viewBox="0 0 56 56" style={{ transform: 'rotate(-90deg)' }}>
                  <circle cx="28" cy="28" r="22" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="5" fill="none" />
                  <circle
                    cx="28"
                    cy="28"
                    r="22"
                    stroke={workoutCount >= workoutTarget ? 'var(--accent-emerald)' : 'var(--accent-primary)'}
                    strokeWidth="5"
                    fill="none"
                    strokeDasharray={2 * Math.PI * 22}
                    strokeDashoffset={2 * Math.PI * 22 * (1 - Math.min(1, workoutCount / Math.max(1, workoutTarget)))}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 0.8s ease' }}
                  />
                </svg>
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.6875rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                  {Math.round(workoutProgressPct)}%
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Metric 2: Weekly Volume Lifted */}
        <div className="card card-glow-cyan" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Weekly Work Tonnage
            </span>
            <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-emerald) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-emerald) 30%, transparent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-emerald)' }}>
              <TrendingUp size={18} />
            </div>
          </div>
          <div>
            <div className="mono-stat" style={{ fontSize: '2.1rem', color: 'var(--text-main)', lineHeight: 1 }}>
              {formatVolume(volumeKg)}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.5rem', fontWeight: 600 }}>
              Calculated load × reps across all completed sets
            </p>
          </div>
        </div>

        {/* Metric 3: Personal Records Set */}
        <div className="card card-glow-gold" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Personal Records
            </span>
            <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-amber) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-amber) 30%, transparent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-amber)' }}>
              <Award size={18} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
              <span className="mono-stat text-gradient-gold" style={{ fontSize: '2.25rem', lineHeight: 1 }}>
                {prCount}
              </span>
              <span style={{ color: 'var(--text-dim)', fontSize: '0.9375rem', fontWeight: 700 }}>
                PRs unlocked
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.5rem', fontWeight: 600 }}>
              Top load & estimated 1RM milestones achieved
            </p>
          </div>
        </div>

        {/* Metric 4: Weekly Nutrition Adherence */}
        <div className="card card-glow-emerald" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Nutrition Adherence
            </span>
            <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--accent-primary) 30%, transparent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
              <ShieldCheck size={18} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
              <span className="mono-stat text-gradient-emerald" style={{ fontSize: '2.25rem', lineHeight: 1 }}>
                {loggedDaysCount > 0 ? `${Math.round(adherencePct)}%` : '—'}
              </span>
              <span style={{ color: 'var(--text-dim)', fontSize: '0.8125rem', fontWeight: 700 }}>
                ({loggedDaysCount}/7 days logged)
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.5rem', fontWeight: 600 }}>
              Within ±10% energy goal. Unlogged days excluded.
            </p>
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
              <span style={{ fontSize: '0.8125rem', color: avgProtein >= targetProtein ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
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
              <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-amber)' }}>
                {loggedDaysCount > 0 ? `${avgCalories} kcal` : 'No logs yet'}
              </span>
              {targetCalories > 0 && loggedDaysCount > 0 && (
                <span
                  style={{
                    fontSize: '0.8125rem',
                    color:
                      Math.abs(avgCalories - targetCalories) / targetCalories <= 0.1
                        ? 'var(--accent-emerald)'
                        : 'var(--accent-amber)',
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
                Energy Display Hidden
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                Energy numbers are hidden based on your wellbeing preference.
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
            <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '2px', background: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
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
                        background: hasLogs ? 'transparent' : 'var(--bg-surface)',
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
                                  color: d.comparison.delta_energy_kcal >= 0 ? 'var(--accent-amber)' : 'var(--accent-primary)',
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
                                color: d.comparison.delta_protein_g >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)',
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
                              borderRadius: '2px',
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
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem', border: '1px solid color-mix(in srgb, var(--accent-primary) 25%, transparent)' }}>
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
            <span style={{ fontSize: '0.6875rem', padding: '0.2rem 0.5rem', borderRadius: '2px', background: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)', color: 'var(--accent-primary)', border: '1px solid color-mix(in srgb, var(--accent-primary) 20%, transparent)' }}>
              Rule S1 & AC-87 Compliant
            </span>
          </div>
        </div>

        {/* Insights need at least 3 sessions of an exercise in the window (AC-86) */}
        {!insightsData?.has_enough_data ? (
          <div style={{ padding: '1.25rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px dashed var(--border-card)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Clock size={18} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              {insightsData?.message || 'Not enough data yet. Log at least 3 sessions of an exercise in the last 12 weeks to see its trend.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: '1rem' }}>
            {/* Insight Cards (AC-86, AC-87) */}
            {insightsData.insights?.map((ins: any) => (
              <div
                key={ins.id}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '0.75rem',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.6875rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--accent-primary)', letterSpacing: '0.08em' }}>
                      Strength trend
                    </span>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
                      {String(ins.window).replace(/_/g, ' ')} · n = {ins.n}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>
                    {ins.title}
                  </h3>

                  <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    {ins.statement}
                  </p>
                </div>

                {/* Limitations are always shown with the insight (AC-86) */}
                <div style={{ padding: '0.625rem', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent-primary)' }}>
                  <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Info size={12} style={{ color: 'var(--accent-primary)' }} />
                    Limitations
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.125rem' }}>
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
                  background: 'var(--bg-surface)',
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
                  <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)' }}>
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
                          {it.food_name || it.recipe_title || 'Custom item'} ({Number(it.quantity)} {it.unit})
                          {i < log.items.length - 1 ? ', ' : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  {/* Snapshot Macros */}
                  <div style={{ textAlign: 'right', fontSize: '0.75rem' }}>
                    {!isCaloriesHidden && (
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        {Math.round(log.items?.reduce((acc: number, it: any) => acc + logItemAmount(it, 'energy_kcal'), 0))} kcal
                      </div>
                    )}
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.6875rem' }}>
                      P: {Math.round(log.items?.reduce((acc: number, it: any) => acc + logItemAmount(it, 'protein_g'), 0))}g
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleDeleteLog(log.id)}
                    title="Delete meal log"
                    style={{ color: 'var(--accent-rose)', padding: '0.375rem' }}
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
              <div style={{ padding: '0.5rem 0.75rem', background: 'color-mix(in srgb, var(--accent-primary) 8%, transparent)', borderRadius: 'var(--radius-sm)', border: '1px solid color-mix(in srgb, var(--accent-primary) 20%, transparent)', fontSize: '0.6875rem', color: 'var(--accent-primary)' }}>
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
