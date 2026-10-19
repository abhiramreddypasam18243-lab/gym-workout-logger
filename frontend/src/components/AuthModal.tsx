import React, { useState } from 'react'
import { Dumbbell, AlertCircle, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'

export const AuthModal: React.FC = () => {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')

  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setFieldErrors({})

    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      setFieldErrors({ email: 'Please enter your email address' })
      return
    }

    // Password validation (SEC1, AC-02: 12-128 characters)
    if (password.length < 12 || password.length > 128) {
      setFieldErrors({ password: 'Password must be between 12 and 128 characters' })
      return
    }

    setIsLoading(true)
    try {
      if (mode === 'login') {
        await login(trimmedEmail, password)
      } else {
        await register(trimmedEmail, password, displayName.trim() || undefined)
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setErrorMessage('Invalid email or password.')
        } else if (err.status === 409) {
          setFieldErrors({ email: 'An account with this email address already exists.' })
        } else if (err.status === 429) {
          setErrorMessage('Too many attempts. Please try again in 15 minutes.')
        } else {
          setErrorMessage(err.message || 'Authentication request failed.')
        }
      } else {
        setErrorMessage('Could not connect to the server. Please check your network.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem 1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: '420px', padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{ display: 'inline-flex', background: 'var(--accent-primary)', width: '48px', height: '48px', borderRadius: 'var(--radius-sm)', alignItems: 'center', justifyContent: 'center', color: 'var(--text-on-accent)', marginBottom: '0.75rem' }}>
            <Dumbbell size={28} strokeWidth={2.5} />
          </div>
          <h1 style={{ fontSize: '1.5rem' }}>Titan Strength</h1>
          <p style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Workout Logger & Strength Diet Planner
          </p>
        </div>

        {/* Tab switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1.5rem' }}>
          <button
            type="button"
            className="btn btn-ghost"
            style={{
              flex: 1,
              borderRadius: 0,
              borderBottom: mode === 'login' ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: mode === 'login' ? 'var(--text-main)' : 'var(--text-dim)',
              fontWeight: 700,
            }}
            onClick={() => {
              setMode('login')
              setErrorMessage(null)
              setFieldErrors({})
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            style={{
              flex: 1,
              borderRadius: 0,
              borderBottom: mode === 'register' ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: mode === 'register' ? 'var(--text-main)' : 'var(--text-dim)',
              fontWeight: 700,
            }}
            onClick={() => {
              setMode('register')
              setErrorMessage(null)
              setFieldErrors({})
            }}
          >
            Create Account
          </button>
        </div>

        {errorMessage && (
          <div style={{ background: 'var(--accent-rose-bg)', border: '1px solid var(--accent-rose-border)', color: 'var(--accent-rose)', padding: '0.625rem 0.875rem', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="alert">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-display-name">Display Name (Optional)</label>
              <input
                id="auth-display-name"
                type="text"
                className="form-input"
                placeholder="e.g. Alex"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="auth-email">Email Address</label>
            <input
              id="auth-email"
              type="email"
              className="form-input"
              placeholder="you@example.com"
              value={email}
              aria-describedby={fieldErrors.email ? 'auth-email-error' : undefined}
              aria-invalid={!!fieldErrors.email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
            {fieldErrors.email && (
              <div id="auth-email-error" className="form-error">{fieldErrors.email}</div>
            )}
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="form-label" htmlFor="auth-password">Password</label>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>12–128 chars</span>
            </div>
            <input
              id="auth-password"
              type="password"
              className="form-input"
              placeholder="Minimum 12 characters"
              value={password}
              aria-describedby={fieldErrors.password ? 'auth-password-error' : undefined}
              aria-invalid={!!fieldErrors.password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
            />
            {fieldErrors.password && (
              <div id="auth-password-error" className="form-error">{fieldErrors.password}</div>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '0.5rem' }}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="spinner" style={{ width: '18px', height: '18px' }} />
            ) : (
              <>
                <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
