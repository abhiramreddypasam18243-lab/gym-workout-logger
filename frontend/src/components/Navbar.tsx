import React from 'react'
import { Dumbbell, Calendar, ClipboardList, Activity, Settings, LogOut, Info, TrendingUp } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export type TabType = 'logger' | 'routines' | 'history' | 'analytics' | 'exercises' | 'profile'

interface NavbarProps {
  activeTab: TabType
  onSelectTab: (tab: TabType) => void
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onSelectTab }) => {
  const { user, profile, units, updateUnits, logout } = useAuth()

  const toggleUnits = () => {
    const next = units === 'kg' ? 'lb' : 'kg'
    updateUnits(next)
  }

  return (
    <header style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(9, 13, 22, 0.95)', position: 'sticky', top: 0, zIndex: 50, backdropFilter: 'blur(12px)' }}>
      {/* Informational Disclaimer (AC-28, S1) */}
      <div className="disclaimer-banner">
        <Info size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
        <span>
          <strong>Informational notice:</strong> Estimates are informational and not medical advice. This app is not a substitute for a registered dietitian or doctor.
        </span>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <div style={{ background: 'linear-gradient(135deg, #0284c7, #38bdf8)', width: '36px', height: '36px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#04111d' }}>
            <Dumbbell size={20} strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.05rem', letterSpacing: '-0.02em', color: '#fff' }}>
              TITAN <span style={{ color: 'var(--accent-primary)' }}>STRENGTH</span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '-2px' }}>
              Workout Logger & Diet Planner
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', overflowX: 'auto', maxWidth: '100%', padding: '0.25rem 0' }} aria-label="Main Navigation">
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'logger' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onSelectTab('logger')}
            aria-current={activeTab === 'logger' ? 'page' : undefined}
          >
            <Dumbbell size={16} />
            <span>Logger</span>
          </button>

          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'routines' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onSelectTab('routines')}
            aria-current={activeTab === 'routines' ? 'page' : undefined}
          >
            <ClipboardList size={16} />
            <span>Routines</span>
          </button>

          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'history' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onSelectTab('history')}
            aria-current={activeTab === 'history' ? 'page' : undefined}
          >
            <Calendar size={16} />
            <span>History</span>
          </button>

          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'analytics' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onSelectTab('analytics')}
            aria-current={activeTab === 'analytics' ? 'page' : undefined}
          >
            <TrendingUp size={16} />
            <span>Strength</span>
          </button>

          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'exercises' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onSelectTab('exercises')}
            aria-current={activeTab === 'exercises' ? 'page' : undefined}
          >
            <Activity size={16} />
            <span>Exercises</span>
          </button>

          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'profile' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onSelectTab('profile')}
            aria-current={activeTab === 'profile' ? 'page' : undefined}
          >
            <Settings size={16} />
            <span>Settings</span>
          </button>
        </nav>

        {/* User controls & Units Toggle (AC-96) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={toggleUnits}
            title="Click to toggle units between kg and lb"
            aria-label={`Toggle units, currently ${units}`}
            style={{ fontWeight: 700, padding: '0.25rem 0.625rem', height: '32px' }}
          >
            <span style={{ color: 'var(--accent-primary)' }}>{units.toUpperCase()}</span>
          </button>

          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                {profile?.display_name || user.email.split('@')[0]}
              </span>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={logout}
                title="Sign out"
                aria-label="Sign out"
                style={{ padding: '0.35rem' }}
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
