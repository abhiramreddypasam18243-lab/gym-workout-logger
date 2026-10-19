import React from 'react'
import {
  Dumbbell,
  Calendar,
  ClipboardList,
  Activity,
  Settings,
  LogOut,
  Info,
  TrendingUp,
  Utensils,
  Sparkles,
  LayoutDashboard,
  Search,
  Timer,
  Volume2,
  VolumeX,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { isSoundEnabled, setSoundEnabled, playMicroClick } from '../utils/audio'
import { AVAILABLE_THEMES, getStoredTheme, applyTheme, type ThemeId } from '../utils/theme'

export type TabType =
  | 'dashboard'
  | 'logger'
  | 'routines'
  | 'history'
  | 'analytics'
  | 'nutrition'
  | 'mealplan'
  | 'exercises'
  | 'profile'

interface NavbarProps {
  activeTab: TabType
  onSelectTab: (tab: TabType) => void
  onOpenCommandPalette: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  onOpenCommandPalette,
}) => {
  const { user, profile, units, updateUnits, logout } = useAuth()
  const [soundOn, setSoundOn] = React.useState(() => isSoundEnabled())
  const [activeTheme, setActiveTheme] = React.useState<ThemeId>(() => getStoredTheme())

  const handleThemeChange = (newTheme: ThemeId) => {
    setActiveTheme(newTheme)
    applyTheme(newTheme)
    playMicroClick()
  }

  const toggleUnits = () => {
    const next = units === 'kg' ? 'lb' : 'kg'
    updateUnits(next)
    playMicroClick()
  }

  const toggleSound = () => {
    const next = !soundOn
    setSoundOn(next)
    setSoundEnabled(next)
    if (next) playMicroClick()
  }

  const openTimer = () => {
    window.dispatchEvent(new CustomEvent('titan-start-timer', { detail: { seconds: 90 } }))
    playMicroClick()
  }

  const navItems: { tab: TabType; label: string; icon: React.ReactNode }[] = [
    { tab: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
    { tab: 'logger', label: 'Workout', icon: <Dumbbell size={16} /> },
    { tab: 'routines', label: 'Routines', icon: <ClipboardList size={16} /> },
    { tab: 'history', label: 'History', icon: <Calendar size={16} /> },
    { tab: 'analytics', label: 'Strength', icon: <TrendingUp size={16} /> },
    { tab: 'nutrition', label: 'Nutrition', icon: <Utensils size={16} /> },
    { tab: 'mealplan', label: 'Meal Plan', icon: <Sparkles size={16} /> },
    { tab: 'exercises', label: 'Catalogue', icon: <Activity size={16} /> },
    { tab: 'profile', label: 'Settings', icon: <Settings size={16} /> },
  ]

  return (
    <header
      style={{
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'var(--bg-surface)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
      }}
    >
      {/* Informational Disclaimer (AC-28, S1) */}
      <div className="disclaimer-banner">
        <Info size={13} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
        <span>
          <strong>Titan Intelligence:</strong> Estimates and recommendations are strictly informational and non-medical.
        </span>
      </div>

      <div
        style={{
          maxWidth: '1360px',
          margin: '0 auto',
          padding: '0.65rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        {/* Brand Logo with Glow */}
        <div
          style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}
          onClick={() => {
            onSelectTab('dashboard')
            playMicroClick()
          }}
        >
          <div
            style={{
              background: 'var(--accent-primary)',
              width: '38px',
              height: '38px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--bg-surface)',
              boxShadow: 'none',
              flexShrink: 0,
            }}
          >
            <Dumbbell size={22} strokeWidth={2.6} />
          </div>
          <div>
            <div
              style={{
                fontWeight: 900,
                fontSize: '1.15rem',
                letterSpacing: '-0.03em',
                lineHeight: 1.1,
              }}
            >
              <span style={{ color: 'var(--text-main)' }}>TITAN</span>{' '}
              <span className="text-gradient-cyan">STRENGTH</span>
            </div>
            <div
              style={{
                fontSize: '0.6875rem',
                fontWeight: 600,
                color: 'var(--text-dim)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}
            >
              Pro Strength & Diet Suite
            </div>
          </div>
        </div>

        {/* Global Quick Search / Command Palette Bar */}
        <button
          type="button"
          onClick={onOpenCommandPalette}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.4rem 0.85rem',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.09)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-dim)',
            fontSize: '0.8125rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--accent-primary) 40%, transparent)'
            e.currentTarget.style.color = 'var(--text-muted)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.09)'
            e.currentTarget.style.color = 'var(--text-dim)'
          }}
          title="Search or press Ctrl+K"
          aria-label="Open Command Palette"
        >
          <Search size={14} style={{ color: 'var(--accent-primary)' }} />
          <span>Search or Ctrl+K</span>
          <span
            style={{
              background: 'rgba(255, 255, 255, 0.07)',
              padding: '1px 5px',
              borderRadius: '2px',
              fontSize: '0.6875rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
            }}
          >
            ⌘K
          </span>
        </button>

        {/* Navigation Tabs Pill Container */}
        <nav
          className="nav-scroll"
          aria-label="Main Navigation"
          style={{
            background: 'var(--bg-surface)',
            padding: '4px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
          }}
        >
          {navItems.map((item) => {
            const isActive = activeTab === item.tab
            return (
              <button
                key={item.tab}
                type="button"
                className={`btn btn-sm ${isActive ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => {
                  onSelectTab(item.tab)
                  playMicroClick()
                }}
                aria-current={isActive ? 'page' : undefined}
                style={{
                  borderRadius: 'var(--radius-sm)',
                  fontWeight: isActive ? 800 : 600,
                  transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                  boxShadow: isActive ? 'none' : 'none',
                }}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        {/* Right Utility Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {/* Quick Rest Timer Trigger */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={openTimer}
            title="Start Rest Timer (90s)"
            style={{ padding: '0.35rem 0.65rem', height: '34px' }}
          >
            <Timer size={15} style={{ color: 'var(--accent-primary)' }} />
            <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>90s</span>
          </button>

          {/* Sound Toggle */}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={toggleSound}
            title={soundOn ? 'Sound On' : 'Sound Muted'}
            aria-label="Toggle Sound"
            style={{ padding: '0.35rem', height: '34px', width: '34px' }}
          >
            {soundOn ? (
              <Volume2 size={16} style={{ color: 'var(--accent-primary)' }} />
            ) : (
              <VolumeX size={16} style={{ color: 'var(--text-dim)' }} />
            )}
          </button>

          {/* Dynamic Athletic Theme Selector (Cyber Cyan, Hyper Violet, Volt Lime, Solar Amber) */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--bg-surface)',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
            title="Change Athletic Color Theme"
          >
            {AVAILABLE_THEMES.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`theme-pill ${activeTheme === t.id ? 'active' : ''}`}
                style={{
                  background: t.gradient,
                  outline: 'none',
                }}
                onClick={() => handleThemeChange(t.id)}
                title={`Theme: ${t.name} (${t.label})`}
                aria-label={`Select ${t.name} theme`}
              />
            ))}
          </div>

          {/* Units Switcher */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={toggleUnits}
            title="Toggle weight units"
            aria-label={`Toggle units, currently ${units}`}
            style={{ fontWeight: 800, padding: '0.25rem 0.65rem', height: '34px', fontFamily: 'var(--font-mono)' }}
          >
            <span style={{ color: 'var(--accent-primary)' }}>{units.toUpperCase()}</span>
          </button>

          {/* User Profile / Logout */}
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '0.25rem' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'var(--accent-primary-soft)',
                  border: '1px solid color-mix(in srgb, var(--accent-primary) 35%, transparent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '0.8125rem',
                  color: 'var(--text-main)',
                }}
                title={profile?.display_name || user.email}
              >
                {(profile?.display_name || user.email)[0].toUpperCase()}
              </div>

              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={logout}
                title="Sign out"
                aria-label="Sign out"
                style={{ padding: '0.35rem', height: '34px', width: '34px' }}
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
