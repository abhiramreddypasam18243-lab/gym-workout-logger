import React, { useState, useEffect, useRef } from 'react'
import { Search, Dumbbell, Utensils, TrendingUp, Calendar, ClipboardList, Sparkles, Activity, X, ArrowRight } from 'lucide-react'
import { api } from '../api/client'
import { AVAILABLE_THEMES, applyTheme } from '../utils/theme'
import type { Exercise } from '../types'
import type { TabType } from './Navbar'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onSelectTab: (tab: TabType) => void
  onSelectExercise?: (exercise: Exercise) => void
}

interface CommandItem {
  id: string
  title: string
  subtitle: string
  category: 'Navigation' | 'Exercises' | 'Nutrition' | 'Action'
  icon: React.ReactNode
  onSelect: () => void
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectTab,
  onSelectExercise,
}) => {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [exercises, setExercises] = useState<Exercise[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  // Load exercises on mount
  useEffect(() => {
    api.getExercises()
      .then(setExercises)
      .catch(() => {})
  }, [])

  // Auto focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Navigation commands
  const defaultCommands: CommandItem[] = [
    {
      id: 'nav-dashboard',
      title: 'Performance Dashboard',
      subtitle: 'Overview, weekly volume, PRs, adherence',
      category: 'Navigation',
      icon: <Activity size={16} className="text-cyan-400" />,
      onSelect: () => onSelectTab('dashboard'),
    },
    {
      id: 'nav-logger',
      title: 'Active Workout Logger',
      subtitle: 'Record sets, track RPE, progressive overload',
      category: 'Navigation',
      icon: <Dumbbell size={16} className="text-cyan-400" />,
      onSelect: () => onSelectTab('logger'),
    },
    {
      id: 'nav-routines',
      title: 'Workout Routines',
      subtitle: 'Manage splits, PPL, upper/lower templates',
      category: 'Navigation',
      icon: <ClipboardList size={16} className="text-cyan-400" />,
      onSelect: () => onSelectTab('routines'),
    },
    {
      id: 'nav-analytics',
      title: 'Strength Analytics & 1RM Progression',
      subtitle: 'E1RM curves, personal records, consistency matrix',
      category: 'Navigation',
      icon: <TrendingUp size={16} className="text-cyan-400" />,
      onSelect: () => onSelectTab('analytics'),
    },
    {
      id: 'nav-mealplan',
      title: 'Meal Plan & Grocery List',
      subtitle: '7-day strength macro plan and substitution engine',
      category: 'Nutrition',
      icon: <Sparkles size={16} className="text-amber-400" />,
      onSelect: () => onSelectTab('mealplan'),
    },
    {
      id: 'nav-nutrition',
      title: 'Nutrition Targets & Preferences',
      subtitle: 'TDEE calculator, macro splits, allergies',
      category: 'Nutrition',
      icon: <Utensils size={16} className="text-amber-400" />,
      onSelect: () => onSelectTab('nutrition'),
    },
    {
      id: 'nav-history',
      title: 'Workout History & Logs',
      subtitle: 'Review past sessions, volumes, and set history',
      category: 'Navigation',
      icon: <Calendar size={16} className="text-cyan-400" />,
      onSelect: () => onSelectTab('history'),
    },
    {
      id: 'action-rest-timer',
      title: 'Start 90s Rest Timer',
      subtitle: 'Quick trigger recovery countdown',
      category: 'Action',
      icon: <Activity size={16} className="text-emerald-400" />,
      onSelect: () => {
        window.dispatchEvent(new CustomEvent('titan-start-timer', { detail: { seconds: 90 } }))
      },
    },
    {
      id: 'action-morale-boost',
      title: 'Boost Morale (Daily Motivation)',
      subtitle: 'View uplifting quotes to fuel your training session',
      category: 'Action',
      icon: <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} />,
      onSelect: () => {
        onSelectTab('dashboard')
      },
    },
    ...AVAILABLE_THEMES.map((t) => ({
      id: `theme-${t.id}`,
      title: `Switch Theme: ${t.name}`,
      subtitle: `Switch color scheme to ${t.label}`,
      category: 'Action' as const,
      icon: <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: t.gradient, display: 'inline-block' }} />,
      onSelect: () => {
        applyTheme(t.id)
      },
    })),
  ]

  // Filter exercises based on query
  const exerciseCommands: CommandItem[] = exercises
    .filter((ex) =>
      ex.name.toLowerCase().includes(query.toLowerCase()) ||
      ex.primary_muscle.toLowerCase().includes(query.toLowerCase()) ||
      ex.equipment.toLowerCase().includes(query.toLowerCase())
    )
    .slice(0, 8)
    .map((ex) => ({
      id: `ex-${ex.id}`,
      title: ex.name,
      subtitle: `${ex.primary_muscle.toUpperCase()} • ${ex.equipment}`,
      category: 'Exercises',
      icon: <Dumbbell size={16} style={{ color: 'var(--accent-primary)' }} />,
      onSelect: () => {
        if (onSelectExercise) onSelectExercise(ex)
        onSelectTab('exercises')
      },
    }))

  const filteredCommands: CommandItem[] = query.trim()
    ? [
        ...defaultCommands.filter(
          (c) =>
            c.title.toLowerCase().includes(query.toLowerCase()) ||
            c.subtitle.toLowerCase().includes(query.toLowerCase())
        ),
        ...exerciseCommands,
      ]
    : defaultCommands

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredCommands.length))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) =>
          prev === 0 ? Math.max(0, filteredCommands.length - 1) : prev - 1
        )
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].onSelect()
          onClose()
        }
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, filteredCommands, selectedIndex, onClose])

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'var(--bg-surface)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '10vh',
        animation: 'fadeIn 0.15s ease',
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '580px',
          padding: 0,
          background: 'var(--bg-surface)',
          border: '1px solid color-mix(in srgb, var(--accent-primary) 30%, transparent)',
          boxShadow: 'none',
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '1rem 1.25rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <Search size={18} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            placeholder="Search exercises, routines, foods, or jump to tab..."
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              color: 'var(--text-main)',
              fontSize: '1rem',
              fontFamily: 'inherit',
            }}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
            >
              <X size={16} />
            </button>
          )}
          <span
            style={{
              fontSize: '0.6875rem',
              color: 'var(--text-dim)',
              background: 'rgba(255, 255, 255, 0.06)',
              padding: '2px 6px',
              borderRadius: '2px',
              fontWeight: 600,
            }}
          >
            ESC
          </span>
        </div>

        {/* Results List */}
        <div style={{ maxHeight: '380px', overflowY: 'auto', padding: '0.5rem' }}>
          {filteredCommands.length === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.875rem' }}>
              No matches found for "{query}".
            </div>
          ) : (
            filteredCommands.map((item, idx) => {
              const isSelected = idx === selectedIndex
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.onSelect()
                    onClose()
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.625rem 0.875rem',
                    borderRadius: 'var(--radius-sm)',
                    background: isSelected ? 'color-mix(in srgb, var(--accent-primary) 12%, transparent)' : 'transparent',
                    border: isSelected ? '1px solid color-mix(in srgb, var(--accent-primary) 25%, transparent)' : '1px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.1s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: 'var(--radius-sm)',
                        background: isSelected ? 'color-mix(in srgb, var(--accent-primary) 20%, transparent)' : 'rgba(255, 255, 255, 0.05)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {item.icon}
                    </div>
                    <div style={{ overflow: 'hidden' }}>
                      <div
                        style={{
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          color: isSelected ? 'var(--text-main)' : 'var(--text-main)',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                          overflow: 'hidden',
                        }}
                      >
                        {item.title}
                      </div>
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: isSelected ? 'var(--text-muted)' : 'var(--text-dim)',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                          overflow: 'hidden',
                        }}
                      >
                        {item.subtitle}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        color: 'var(--text-dim)',
                        background: 'rgba(255, 255, 255, 0.04)',
                        padding: '2px 6px',
                        borderRadius: '2px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                      }}
                    >
                      {item.category}
                    </span>
                    {isSelected && <ArrowRight size={14} style={{ color: 'var(--accent-primary)' }} />}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer shortcuts hint */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.625rem 1.25rem',
            background: 'rgba(0, 0, 0, 0.3)',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            fontSize: '0.6875rem',
            color: 'var(--text-dim)',
          }}
        >
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span>Titan Command Center</span>
        </div>
      </div>
    </div>
  )
}
