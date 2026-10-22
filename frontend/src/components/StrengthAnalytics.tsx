import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  TrendingUp,
  Trophy,
  Calendar,
  Dumbbell,
  AlertCircle,
  Table as TableIcon,
  Sparkles,
  Activity,
} from 'lucide-react'
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
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

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
    setHoveredIdx(null)
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

  // Derived metrics
  const { allTimeBest, e1rmGain, maxE1rm, minE1rm } = useMemo(() => {
    if (trends.length === 0) {
      return { allTimeBest: 0, e1rmGain: 0, maxE1rm: 100, minE1rm: 0 }
    }
    const values = trends.map((t) => Number(t.e1rm) || 0)
    const best = Math.max(...values)
    const first = values[0]
    const gain = best - first
    return {
      allTimeBest: best,
      e1rmGain: gain,
      maxE1rm: Math.max(...values),
      // The top-set line shares the axis, and a top set is never above that day's e1RM
      minE1rm: Math.min(...values, ...trends.map((t) => Number(t.top_set_load ?? t.e1rm) || 0)),
    }
  }, [trends])

  // SVG Chart Geometry Calculations
  const chartGeometry = useMemo(() => {
    if (trends.length === 0) return null

    const width = 720
    const height = 250
    const pad = { top: 35, right: 35, bottom: 45, left: 55 }
    const plotW = width - pad.left - pad.right
    const plotH = height - pad.top - pad.bottom

    const minVal = Math.max(0, Math.floor(minE1rm * 0.9))
    const maxVal = Math.ceil(maxE1rm * 1.08)
    const range = maxVal - minVal || 1

    const points = trends.map((t, idx) => {
      const x = trends.length === 1
        ? pad.left + plotW / 2
        : pad.left + (idx / (trends.length - 1)) * plotW
      const val = Number(t.e1rm) || 0
      const y = pad.top + plotH - ((val - minVal) / range) * plotH
      return { x, y, data: t, idx }
    })

    // Heaviest working set per day (D-33): actual weight lifted, drawn straight, not smoothed
    const topPoints = points.map((pt) => {
      const val = Number(pt.data.top_set_load ?? pt.data.load) || 0
      return { x: pt.x, y: pad.top + plotH - ((val - minVal) / range) * plotH }
    })
    const topPath = topPoints.length === 1
      ? `M ${topPoints[0].x - 40} ${topPoints[0].y} L ${topPoints[0].x + 40} ${topPoints[0].y}`
      : topPoints.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`).join(' ')

    // Generate smooth cubic bezier SVG path
    let curvePath = ''
    if (points.length === 1) {
      curvePath = `M ${points[0].x - 40} ${points[0].y} L ${points[0].x + 40} ${points[0].y}`
    } else {
      curvePath = `M ${points[0].x} ${points[0].y}`
      for (let i = 0; i < points.length - 1; i++) {
        const curr = points[i]
        const next = points[i + 1]
        const cx1 = curr.x + (next.x - curr.x) / 2
        const cy1 = curr.y
        const cx2 = curr.x + (next.x - curr.x) / 2
        const cy2 = next.y
        curvePath += ` C ${cx1} ${cy1}, ${cx2} ${cy2}, ${next.x} ${next.y}`
      }
    }

    // Area closed path for gradient fill
    const areaBottom = pad.top + plotH
    const areaPath = points.length === 1
      ? `${curvePath} L ${points[0].x + 40} ${areaBottom} L ${points[0].x - 40} ${areaBottom} Z`
      : `${curvePath} L ${points[points.length - 1].x} ${areaBottom} L ${points[0].x} ${areaBottom} Z`

    // Grid tick lines (4 horizontal steps)
    const gridTicks = [0, 0.33, 0.66, 1].map((pct) => {
      const val = Math.round(minVal + pct * range)
      const y = pad.top + plotH - pct * plotH
      return { val, y }
    })

    return { width, height, pad, plotW, plotH, minVal, maxVal, points, topPoints, topPath, curvePath, areaPath, gridTicks, areaBottom }
  }, [trends, minE1rm, maxE1rm])

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
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
              <TrendingUp style={{ color: 'var(--accent-primary)' }} size={20} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.65rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
                Strength Analytics
              </h1>
              <p style={{ marginTop: '0.15rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                Epley estimated 1RM trajectory, record milestones & volume adherence
              </p>
            </div>
          </div>
        </div>

        {/* View toggle (AC-93: Table alternative for accessibility) */}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setShowDataTable(!showDataTable)}
          aria-label={showDataTable ? 'Show Visual Chart' : 'Show Data Table Alternative'}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}
        >
          <TableIcon size={14} />
          <span>{showDataTable ? 'View Visual Curve' : 'Accessible Data Table'}</span>
        </button>
      </div>

      {errorMessage && (
        <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Movement & Window Selector Dashboard */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 300px' }}>
            <label className="form-label" htmlFor="exercise-select" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Dumbbell size={14} style={{ color: 'var(--accent-primary)' }} />
              Active Movement / Exercise
            </label>
            <select
              id="exercise-select"
              className="form-select"
              value={selectedExerciseId}
              onChange={(e) => setSelectedExerciseId(e.target.value)}
              style={{ fontWeight: 600 }}
            >
              {exercises.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.name} • {ex.primary_muscle.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div style={{ flex: '0 1 200px' }}>
            <label className="form-label" htmlFor="window-select" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Calendar size={14} style={{ color: 'var(--accent-primary)' }} />
              Observation Window
            </label>
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

          {selectedExercise && (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', paddingBottom: '0.35rem' }}>
              <span className="badge badge-blue">
                {selectedExercise.primary_muscle}
              </span>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)', border: '1px solid var(--border-subtle)' }}>
                {selectedExercise.equipment}
              </span>
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="card skeleton" style={{ height: '300px' }} />
          <div className="card skeleton" style={{ height: '160px' }} />
        </div>
      ) : trends.length === 0 ? (
        <div className="empty-state" style={{ marginBottom: '1.5rem', padding: '3.5rem 1.5rem' }}>
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
          <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>No strength sessions recorded for this movement</h3>
          <p style={{ maxWidth: '480px', margin: '0 auto' }}>
            Log working sets for <strong>{selectedExercise?.name}</strong> in the Workout Logger to generate real-time e1RM trajectory curves and personal record milestones.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
          {/* Level 100 KPI Telemetry Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div className="card card-glow-cyan" style={{ padding: '1.15rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
                  Current Best e1RM
                </span>
                <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
                <span style={{ fontSize: '1.85rem', fontWeight: 900, color: 'var(--text-main)', fontFamily: 'var(--font-display)' }}>
                  {allTimeBest}
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--accent-primary)', fontWeight: 700 }}>
                  {isLb ? 'lb' : 'kg'}
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem', display: 'block' }}>
                Formula: load × (1 + reps/30)
              </span>
            </div>

            <div className="card card-glow-gold" style={{ padding: '1.15rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
                  Window Delta Gain
                </span>
                <Trophy size={16} style={{ color: 'var(--accent-amber)' }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
                <span style={{
                  fontSize: '1.85rem',
                  fontWeight: 900,
                  color: e1rmGain >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                  fontFamily: 'var(--font-display)',
                  display: 'flex',
                  alignItems: 'center',
                }}>
                  {e1rmGain >= 0 ? `+${e1rmGain.toFixed(1)}` : e1rmGain.toFixed(1)}
                </span>
                <span style={{ fontSize: '0.875rem', color: e1rmGain >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)', fontWeight: 700 }}>
                  {isLb ? 'lb' : 'kg'}
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem', display: 'block' }}>
                Compared to {trends[0]?.date} baseline
              </span>
            </div>

            <div className="card" style={{ padding: '1.15rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
                  Logged Sessions
                </span>
                <Activity size={16} style={{ color: 'var(--text-dim)' }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
                <span style={{ fontSize: '1.85rem', fontWeight: 900, color: 'var(--text-main)', fontFamily: 'var(--font-display)' }}>
                  {trends.length}
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-dim)', fontWeight: 600 }}>
                  data points
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.25rem', display: 'block' }}>
                Across {windowDays} days window
              </span>
            </div>
          </div>

          {/* Interactive SVG Area Curve Progression Graph */}
          <div className="card" style={{ padding: '1.5rem', position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.2rem', color: 'var(--text-main)', fontWeight: 800, margin: 0 }}>
                  {selectedExercise?.name} — 1RM Trajectory
                </h2>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'block', marginTop: '0.2rem' }}>
                  Epley Formula: load × (1 + reps/30). Excludes warmup sets (AC-39).
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-live">
                  <span className="pulse-dot" />
                  Live Model
                </span>
              </div>
            </div>

            {/* Visual Chart or Data Table (AC-93) */}
            {showDataTable ? (
              <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '340px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      <th style={{ padding: '0.65rem 0.5rem' }}>Date</th>
                      <th style={{ padding: '0.65rem 0.5rem' }}>Best Set (Load × Reps)</th>
                      <th style={{ padding: '0.65rem 0.5rem' }}>Estimated 1RM</th>
                      <th style={{ padding: '0.65rem 0.5rem' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.map((t, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', transition: 'background 0.15s ease' }}>
                        <td style={{ padding: '0.65rem 0.5rem', color: 'var(--text-main)', fontFamily: 'var(--font-display)', fontSize: '0.8125rem' }}>
                          {t.date}
                        </td>
                        <td style={{ padding: '0.65rem 0.5rem', color: 'var(--text-main)', fontSize: '0.8125rem' }}>
                          {t.load} {t.unit} × {t.reps}
                        </td>
                        <td style={{ padding: '0.65rem 0.5rem', fontWeight: 700, color: 'var(--accent-primary)', fontFamily: 'var(--font-display)', fontSize: '0.875rem' }}>
                          {t.e1rm} {t.unit}
                        </td>
                        <td style={{ padding: '0.65rem 0.5rem' }}>
                          <span className="badge badge-blue" style={{ fontSize: '0.6875rem' }}>Calculated</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : chartGeometry ? (
              <div style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
                {/* SVG Area spline graph */}
                <svg
                  viewBox={`0 0 ${chartGeometry.width} ${chartGeometry.height}`}
                  style={{ width: '100%', height: 'auto', display: 'block', minWidth: '550px' }}
                  role="img"
                  aria-label="Estimated 1RM and top-set weight over time"
                >
                  <defs>
                    <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" style={{ stopColor: 'var(--accent-primary)' }} stopOpacity="0.4" />
                      <stop offset="60%" style={{ stopColor: 'var(--accent-primary)' }} stopOpacity="0.12" />
                      <stop offset="100%" style={{ stopColor: 'var(--accent-primary)' }} stopOpacity="0.0" />
                    </linearGradient>
                    <filter id="glowNode" x="-30%" y="-30%" width="160%" height="160%">
                      <feGaussianBlur stdDeviation="3" result="blur" />
                      <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  {/* Horizontal Grid lines */}
                  {chartGeometry.gridTicks.map((tick, i) => (
                    <g key={i}>
                      <line
                        x1={chartGeometry.pad.left}
                        y1={tick.y}
                        x2={chartGeometry.width - chartGeometry.pad.right}
                        y2={tick.y}
                        stroke="rgba(255, 255, 255, 0.07)"
                        strokeDasharray="4 4"
                      />
                      <text
                        x={chartGeometry.pad.left - 10}
                        y={tick.y + 4}
                        style={{ fill: 'var(--text-dim)' }}
                        fontSize="10"
                        fontFamily="Barlow Condensed, Arial Narrow, sans-serif"
                        textAnchor="end"
                      >
                        {tick.val}
                      </text>
                    </g>
                  ))}

                  {/* Shaded Area fill */}
                  <path
                    d={chartGeometry.areaPath}
                    fill="url(#curveGradient)"
                  />

                  {/* Spline Curve Line */}
                  <path
                    d={chartGeometry.curvePath}
                    fill="none"
                    style={{ stroke: 'var(--accent-primary)' }}
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Top-set line */}
                  <path
                    d={chartGeometry.topPath}
                    fill="none"
                    style={{ stroke: 'var(--text-muted)' }}
                    strokeWidth="2"
                    strokeDasharray="6 5"
                  />
                  {chartGeometry.topPoints.map((pt, i) => (
                    <rect key={`top-${i}`} x={pt.x - 3.5} y={pt.y - 3.5} width={7} height={7} style={{ fill: 'var(--text-muted)' }} />
                  ))}

                  {/* Data Nodes */}
                  {chartGeometry.points.map((pt) => {
                    const isHovered = hoveredIdx === pt.idx
                    const isAllTimeMax = Number(pt.data.e1rm) === allTimeBest

                    return (
                      <g
                        key={pt.idx}
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredIdx(pt.idx)}
                        onMouseLeave={() => setHoveredIdx(null)}
                      >
                        {/* Invisible larger hit target */}
                        <circle cx={pt.x} cy={pt.y} r={18} fill="transparent" />

                        {/* Outer Glow Halo on hover or PR */}
                        {(isHovered || isAllTimeMax) && (
                          <circle
                            cx={pt.x}
                            cy={pt.y}
                            r={isHovered ? 12 : 9}
                            fill="none"
                            stroke={isAllTimeMax ? 'var(--accent-amber)' : 'var(--accent-primary)'}
                            strokeWidth="2"
                            strokeOpacity={isHovered ? 0.9 : 0.5}
                          />
                        )}

                        {/* Core Circle */}
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r={isHovered ? 6 : 4.5}
                          fill={isAllTimeMax ? 'var(--accent-amber)' : 'var(--bg-main)'}
                          stroke={isAllTimeMax ? 'var(--text-main)' : 'var(--accent-primary)'}
                          strokeWidth="2"
                        />

                        {/* Gold star milestone marker above all-time max */}
                        {isAllTimeMax && (
                          <g transform={`translate(${pt.x - 7}, ${pt.y - 22})`}>
                            <polygon
                              points="7,0 9,5 14,5 10,8 12,13 7,10 2,13 4,8 0,5 5,5"
                              style={{ fill: 'var(--accent-amber)' }}
                            />
                          </g>
                        )}

                        {/* Date label at bottom */}
                        <text
                          x={pt.x}
                          y={chartGeometry.height - 12}
                          fill={isHovered ? 'var(--accent-primary)' : 'var(--text-dim)'}
                          fontSize="9"
                          fontFamily="Barlow Condensed, Arial Narrow, sans-serif"
                          textAnchor="middle"
                        >
                          {pt.data.date.slice(5)}
                        </text>
                      </g>
                    )
                  })}
                </svg>

                {/* Floating Telemetry HUD Tooltip on Hover */}
                {hoveredIdx !== null && chartGeometry.points[hoveredIdx] && (
                  <div
                    style={{
                      position: 'absolute',
                      top: Math.max(10, chartGeometry.points[hoveredIdx].y - 80),
                      left: `clamp(60px, ${chartGeometry.points[hoveredIdx].x}px, calc(100% - 180px))`,
                      transform: 'translateX(-50%)',
                      background: 'var(--bg-surface)',
                      border: '1px solid color-mix(in srgb, var(--accent-primary) 40%, transparent)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.6rem 0.85rem',
                      boxShadow: 'none',
                      pointerEvents: 'none',
                      zIndex: 20,
                      minWidth: '150px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.25rem' }}>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontFamily: 'var(--font-display)' }}>
                        {chartGeometry.points[hoveredIdx].data.date}
                      </span>
                      {Number(chartGeometry.points[hoveredIdx].data.e1rm) === allTimeBest && (
                        <span className="badge badge-amber" style={{ fontSize: '0.625rem', padding: '0.1rem 0.35rem' }}>
                          ★ PEAK
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '1.15rem', fontWeight: 900, color: 'var(--accent-primary)', fontFamily: 'var(--font-display)' }}>
                      {chartGeometry.points[hoveredIdx].data.e1rm} {chartGeometry.points[hoveredIdx].data.unit}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      Best set: {chartGeometry.points[hoveredIdx].data.load} {chartGeometry.points[hoveredIdx].data.unit} × {chartGeometry.points[hoveredIdx].data.reps} reps
                    </div>
                    {chartGeometry.points[hoveredIdx].data.top_set_load && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Top set: {chartGeometry.points[hoveredIdx].data.top_set_load} {chartGeometry.points[hoveredIdx].data.unit} × {chartGeometry.points[hoveredIdx].data.top_set_reps} reps
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : null}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', flexWrap: 'wrap', gap: '0.5rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'inline-block' }} />
                  Estimated 1RM
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span style={{ width: '14px', borderTop: '2px dashed var(--text-muted)', display: 'inline-block' }} />
                  Top set (heaviest weight)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-amber)', display: 'inline-block' }} />
                  ★ Peak Personal Record
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-display)' }}>
                Unit: {isLb ? 'pounds (lb)' : 'kilograms (kg)'}
              </span>
            </div>
          </div>

          {/* Personal Record Milestones (AC-41) */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'color-mix(in srgb, var(--accent-amber) 15%, transparent)',
                  border: '1px solid color-mix(in srgb, var(--accent-amber) 35%, transparent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Trophy size={18} style={{ color: 'var(--accent-amber)' }} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', fontWeight: 800, margin: 0 }}>
                    Personal Record Milestones
                  </h2>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Verified PR breakthroughs and baseline benchmark
                  </span>
                </div>
              </div>
              <span className="badge badge-amber">
                {prs.length} Records Logged
              </span>
            </div>

            {prs.length === 0 ? (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.8125rem' }}>No PR milestones recorded yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {prs.map((p, idx) => (
                  <div
                    key={p.set_id || idx}
                    style={{
                      background: p.is_pr
                        ? 'var(--bg-surface)'
                        : 'var(--bg-surface)',
                      border: p.is_pr
                        ? '1px solid color-mix(in srgb, var(--accent-emerald) 35%, transparent)'
                        : '1px solid var(--border-card)',
                      padding: '0.9rem 1.15rem',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.75rem',
                      boxShadow: p.is_pr ? 'none' : 'none',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                        <span className={`badge ${p.is_pr ? 'badge-emerald' : 'badge-blue'}`}>
                          {p.is_pr ? '🏆 NEW PR' : 'BASELINE BENCHMARK'}
                        </span>
                        <strong style={{ color: 'var(--text-main)', fontSize: '0.95rem', fontFamily: 'var(--font-display)' }}>
                          {p.load} {p.unit} × {p.reps} reps
                        </strong>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.35rem', display: 'block' }}>
                        Completed on {p.completed_at ? new Date(p.completed_at).toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' }) : '—'}
                      </span>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Estimated 1RM
                      </span>
                      <div style={{
                        fontSize: '1.35rem',
                        fontWeight: 900,
                        color: p.is_pr ? 'var(--accent-emerald)' : 'var(--accent-primary)',
                        fontFamily: 'var(--font-display)',
                      }}>
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
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)',
                    border: '1px solid color-mix(in srgb, var(--accent-primary) 35%, transparent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <Calendar size={18} style={{ color: 'var(--accent-primary)' }} />
                  </div>
                  <div>
                    <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)', fontWeight: 800, margin: 0 }}>
                      Weekly Consistency Heatmap (AC-44)
                    </h2>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      Rolling 8-week target adherence
                    </span>
                  </div>
                </div>

                <span className="badge badge-blue">
                  Target: {consistency.weekly_target} sessions / wk
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(95px, 1fr))', gap: '0.75rem' }}>
                {consistency.weeks.map((w, idx) => {
                  const met = w.session_count >= consistency.weekly_target
                  const progressPct = Math.min(100, Math.round((w.session_count / consistency.weekly_target) * 100))

                  return (
                    <div
                      key={idx}
                      style={{
                        background: met
                          ? 'var(--bg-surface)'
                          : 'var(--bg-surface)',
                        border: met
                          ? '1px solid color-mix(in srgb, var(--accent-emerald) 40%, transparent)'
                          : '1px solid var(--border-card)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '0.85rem 0.5rem',
                        textAlign: 'center',
                        position: 'relative',
                        boxShadow: met ? 'none' : 'none',
                      }}
                    >
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', display: 'block', fontFamily: 'var(--font-display)' }}>
                        {w.week_start.slice(5)}
                      </span>
                      <div style={{
                        fontSize: '1.5rem',
                        fontWeight: 900,
                        color: met ? 'var(--accent-emerald)' : 'var(--text-main)',
                        margin: '0.2rem 0',
                        fontFamily: 'var(--font-display)',
                      }}>
                        {w.session_count}
                      </div>

                      {/* Mini Progress Fill Bar */}
                      <div style={{
                        width: '100%',
                        height: '4px',
                        background: 'rgba(255, 255, 255, 0.08)',
                        borderRadius: '2px',
                        overflow: 'hidden',
                        margin: '0.4rem 0',
                      }}>
                        <div style={{
                          width: `${progressPct}%`,
                          height: '100%',
                          background: met ? 'var(--accent-emerald)' : 'var(--accent-primary)',
                          borderRadius: '2px',
                        }} />
                      </div>

                      <span style={{
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        color: met ? 'var(--accent-emerald)' : 'var(--text-dim)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                      }}>
                        {met ? 'Met Target' : `${progressPct}%`}
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
