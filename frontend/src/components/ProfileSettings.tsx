import React, { useState, useEffect } from 'react'
import {
  Settings,
  Shield,
  Check,
  AlertCircle,
  Heart,
  Download,
  Trash2,
  AlertTriangle,
  FileJson,
  Lock,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

const TIMEZONES = [
  'UTC',
  'Asia/Kolkata',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Australia/Sydney',
]

export const ProfileSettings: React.FC = () => {
  const { profile, units, refreshProfile, confirmAdult, updateUnits, logout } = useAuth()

  const [displayName, setDisplayName] = useState('')
  const [selectedTimezone, setSelectedTimezone] = useState('UTC')
  const [goal, setGoal] = useState('build_strength')
  const [activityLevel, setActivityLevel] = useState('moderate')

  // Wellbeing settings (S7, AC-24, AC-25, AC-26)
  const [caloriesHidden, setCaloriesHidden] = useState(false)
  const [nutritionPaused, setNutritionPaused] = useState(false)
  const [trackBodyWeight, setTrackBodyWeight] = useState(false)
  const [needsProfGuidance, setNeedsProfGuidance] = useState(false)

  // Status
  const [isSaving, setIsSaving] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Data Controls state (AC-88, AC-89)
  const [isExporting, setIsExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    if (profile) {
      setDisplayName(profile.display_name || '')
      setSelectedTimezone(profile.timezone || 'UTC')
      setGoal(profile.goal || 'build_strength')
      setActivityLevel(profile.activity_level || 'moderate')
      setCaloriesHidden(profile.calories_hidden || false)
      setNutritionPaused(profile.nutrition_paused || false)
      setTrackBodyWeight(profile.track_body_weight || false)
      setNeedsProfGuidance(profile.needs_professional_guidance || false)
    }
  }, [profile])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      await api.updateProfile({
        display_name: displayName.trim(),
        timezone: selectedTimezone,
        goal,
        activity_level: activityLevel,
        calories_hidden: caloriesHidden,
        nutrition_paused: nutritionPaused,
        track_body_weight: trackBodyWeight,
        needs_professional_guidance: needsProfGuidance,
      })
      await refreshProfile()
      setSuccessMessage('Profile settings updated successfully.')
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not update profile.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleConfirmAdult = async () => {
    try {
      await confirmAdult()
      setSuccessMessage('Adult confirmation recorded. Nutrition planning is enabled.')
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not confirm adult status.')
    }
  }

  const handleExportData = async () => {
    setIsExporting(true)
    setExportSuccess(null)
    setErrorMessage(null)
    try {
      const data = await api.exportData()
      const totalRecords =
        (data.workout_routines?.length || 0) +
        (data.workout_sessions?.length || 0) +
        (data.meal_plans?.length || 0) +
        (data.nutrition_logs?.length || 0)
      setExportSuccess(
        `Export complete! Downloaded JSON archive with ${totalRecords} primary activity records across all 16 domains.`
      )
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to export user data.')
    } finally {
      setIsExporting(false)
    }
  }

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!deletePassword) {
      setDeleteError('Please enter your password to confirm account deletion.')
      return
    }
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await api.deleteAccount(deletePassword)
      setShowDeleteModal(false)
      await logout()
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete account. Please verify your password.')
      setIsDeleting(false)
    }
  }

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <Settings style={{ color: 'var(--accent-primary)' }} />
          Profile & Wellbeing Settings
        </h1>
        <p style={{ marginTop: '0.25rem' }}>Manage account preferences, units, safety safeguards, and data ownership</p>
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

      {exportSuccess && (
        <div style={{ background: 'var(--accent-cyan-bg, color-mix(in srgb, var(--accent-primary) 10%, transparent))', border: '1px solid var(--accent-cyan-border, color-mix(in srgb, var(--accent-primary) 30%, transparent))', color: 'var(--accent-primary)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} role="status">
          <FileJson size={18} />
          <span>{exportSuccess}</span>
        </div>
      )}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Adult Confirmation Card (S2, AC-17) */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
            <div>
              <h2 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)' }}>
                <Shield size={20} style={{ color: 'var(--accent-primary)' }} />
                Age & Nutrition Eligibility (Rule S2)
              </h2>
              <p style={{ fontSize: '0.8125rem', marginTop: '0.25rem', maxWidth: '500px' }}>
                Per safety specification S2, nutrition targets and plan generation require confirming that you are 18 years or older.
              </p>
            </div>

            <div>
              {profile?.adult_confirmed_at ? (
                <span className="badge badge-emerald" style={{ padding: '0.4rem 0.75rem' }}>
                  <Check size={14} /> Confirmed Adult
                </span>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleConfirmAdult}
                >
                  I am 18 or older
                </button>
              )}
            </div>
          </div>
        </div>

        {/* General Preferences */}
        <div className="card">
          <h2 style={{ fontSize: '1.15rem', marginBottom: '1rem', color: 'var(--text-main)' }}>General Preferences</h2>

          <div className="form-group">
            <label className="form-label" htmlFor="display-name">Display Name</label>
            <input
              id="display-name"
              type="text"
              className="form-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="units-select">Preferred Units (AC-96)</label>
              <select
                id="units-select"
                className="form-select"
                value={units}
                onChange={(e) => updateUnits(e.target.value as 'kg' | 'lb')}
              >
                <option value="kg">Metric (kg / cm)</option>
                <option value="lb">Imperial (lb)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="timezone-select">Timezone (AC-15, AC-36)</label>
              <select
                id="timezone-select"
                className="form-select"
                value={selectedTimezone}
                onChange={(e) => setSelectedTimezone(e.target.value)}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="goal-select">Training Goal (S6: No Deficits)</label>
              <select
                id="goal-select"
                className="form-select"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              >
                <option value="build_strength">Build Strength (+5% surplus)</option>
                <option value="maintain">Maintain Current Weight</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="activity-select">Daily Activity Level</label>
              <select
                id="activity-select"
                className="form-select"
                value={activityLevel}
                onChange={(e) => setActivityLevel(e.target.value)}
              >
                <option value="sedentary">Sedentary (desk job, 1.2)</option>
                <option value="light">Lightly Active (1-3 days/wk, 1.375)</option>
                <option value="moderate">Moderately Active (3-5 days/wk, 1.55)</option>
                <option value="heavy">Very Active (6-7 days/wk, 1.725)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Wellbeing Safeguards (S7) */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Heart size={20} style={{ color: 'var(--accent-rose)' }} />
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-main)' }}>Wellbeing & Privacy Controls (Rule S7)</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Hide Calories */}
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={caloriesHidden}
                onChange={(e) => setCaloriesHidden(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)', marginTop: '2px' }}
              />
              <div>
                <strong style={{ color: 'var(--text-main)', fontSize: '0.875rem' }}>Hide Calorie Numbers (AC-24)</strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Hides calorie and kcal displays across all screens. Macros (protein, carbs, fat) remain visible.
                </p>
              </div>
            </label>

            {/* Pause Nutrition */}
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={nutritionPaused}
                onChange={(e) => setNutritionPaused(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)', marginTop: '2px' }}
              />
              <div>
                <strong style={{ color: 'var(--text-main)', fontSize: '0.875rem' }}>Pause Nutrition Features (AC-25)</strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Disables diet planning and food logging while keeping all your workout logging features active.
                </p>
              </div>
            </label>

            {/* Track Body Weight */}
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={trackBodyWeight}
                onChange={(e) => setTrackBodyWeight(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)', marginTop: '2px' }}
              />
              <div>
                <strong style={{ color: 'var(--text-main)', fontSize: '0.875rem' }}>Opt-in: Track Body Weight (AC-26)</strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Disabled by default. Body weight is never requested or charted unless you opt in.
                </p>
              </div>
            </label>

            {/* Needs Professional Guidance */}
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={needsProfGuidance}
                onChange={(e) => setNeedsProfGuidance(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)', marginTop: '2px' }}
              />
              <div>
                <strong style={{ color: 'var(--text-main)', fontSize: '0.875rem' }}>Working with a Healthcare Professional (Rule S3, AC-18)</strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Disables automated estimates and requires manual targets as directed by your dietitian or doctor.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Submit */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSaving}
          >
            {isSaving ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : null}
            <span>Save Settings</span>
          </button>
        </div>
      </form>

      {/* Data Controls & Privacy (AC-88, AC-89) */}
      <div style={{ marginTop: '2.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>
          <FileJson style={{ color: 'var(--accent-cyan, var(--accent-primary))' }} />
          Data Controls & Privacy Rights
        </h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-dim)', marginBottom: '1.25rem' }}>
          Complete data sovereignty under GDPR / CCPA. Export your full personal history in schema-validated JSON or permanently delete your account.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {/* Export Personal Data Card (AC-88) */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.75rem' }}>
                <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)', color: 'var(--accent-primary)' }}>
                  <Download size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1rem', color: 'var(--text-main)', margin: 0 }}>Export All Personal Data (AC-88)</h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Validated against published JSON Schema</span>
                </div>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-dim)', lineHeight: 1.5, marginBottom: '1rem' }}>
                Downloads a single comprehensive JSON archive containing all 16 user-owned domains: workout routines, completed sessions, logged sets, meal plans, items, nutrition logs, preferences, and goals.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-outline"
              onClick={handleExportData}
              disabled={isExporting}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', width: '100%' }}
            >
              {isExporting ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : <Download size={16} />}
              <span>{isExporting ? 'Generating JSON Export...' : 'Download My Data (JSON)'}</span>
            </button>
          </div>

          {/* Danger Zone: Account Deletion Card (AC-89) */}
          <div
            className="card"
            style={{
              borderColor: 'color-mix(in srgb, var(--accent-rose) 30%, transparent)',
              background: 'var(--accent-rose-bg)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.75rem' }}>
                <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', background: 'color-mix(in srgb, var(--accent-rose) 15%, transparent)', color: 'var(--accent-rose)' }}>
                  <Trash2 size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1rem', color: 'var(--accent-rose)', margin: 0 }}>Delete Account (AC-89)</h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Permanent & Irreversible</span>
                </div>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-dim)', lineHeight: 1.5, marginBottom: '1rem' }}>
                Permanently purges all your data across all 16 user tables (sessions, routines, workouts, meal plans, nutrition logs). Requires your password to prevent unauthorized erasure. Shared food and exercise catalogue remains untouched.
              </p>
            </div>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setShowDeleteModal(true)
                setDeleteError(null)
                setDeletePassword('')
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                width: '100%',
                background: 'color-mix(in srgb, var(--accent-rose) 15%, transparent)',
                color: 'var(--accent-rose)',
                border: '1px solid color-mix(in srgb, var(--accent-rose) 30%, transparent)',
              }}
            >
              <Trash2 size={16} />
              <span>Delete My Account</span>
            </button>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal (AC-89) */}
      {showDeleteModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            zIndex: 1000,
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
        >
          <div
            className="card"
            style={{
              maxWidth: '460px',
              width: '100%',
              border: '1px solid color-mix(in srgb, var(--accent-rose) 40%, transparent)',
              boxShadow: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ padding: '0.625rem', borderRadius: '50%', background: 'color-mix(in srgb, var(--accent-rose) 20%, transparent)', color: 'var(--accent-rose)' }}>
                <AlertTriangle size={24} />
              </div>
              <div>
                <h3 id="delete-dialog-title" style={{ fontSize: '1.15rem', color: 'var(--text-main)', margin: 0 }}>
                  Confirm Permanent Deletion
                </h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Action cannot be undone</span>
              </div>
            </div>

            <p style={{ fontSize: '0.875rem', color: 'var(--text-dim)', marginBottom: '1.25rem', lineHeight: 1.5 }}>
              This will permanently erase all your personal data, workouts, routine templates, meal plans, and logs. Please enter your account password to authorize this action:
            </p>

            {deleteError && (
              <div
                style={{
                  background: 'var(--accent-rose-bg)',
                  border: '1px solid var(--accent-rose-border)',
                  color: 'var(--accent-rose)',
                  padding: '0.625rem 0.875rem',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '1rem',
                  fontSize: '0.8125rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <AlertCircle size={16} />
                <span>{deleteError}</span>
              </div>
            )}

            <form onSubmit={handleDeleteAccount}>
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label" htmlFor="delete-account-password">
                  Account Password
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="delete-account-password"
                    type="password"
                    className="form-input"
                    placeholder="Enter your current password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    autoFocus
                    required
                    style={{ paddingLeft: '2.5rem' }}
                  />
                  <Lock
                    size={16}
                    style={{
                      position: 'absolute',
                      left: '0.875rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      color: 'var(--text-muted)',
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowDeleteModal(false)}
                  disabled={isDeleting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn"
                  disabled={isDeleting}
                  style={{
                    background: 'var(--accent-rose)',
                    color: 'var(--text-main)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  {isDeleting ? <span className="spinner" style={{ width: '16px', height: '16px' }} /> : <Trash2 size={16} />}
                  <span>{isDeleting ? 'Deleting Everything...' : 'Permanently Delete'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

