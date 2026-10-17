import React, { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { Navbar, type TabType } from './components/Navbar'
import { Dashboard } from './components/Dashboard'
import { WorkoutLogger } from './components/WorkoutLogger'
import { RoutinesManager } from './components/RoutinesManager'
import { WorkoutHistory } from './components/WorkoutHistory'
import { StrengthAnalytics } from './components/StrengthAnalytics'
import { NutritionPlanner } from './components/NutritionPlanner'
import { MealPlanView } from './components/MealPlanView'
import { ExercisesCatalogue } from './components/ExercisesCatalogue'
import { ProfileSettings } from './components/ProfileSettings'
import { AuthModal } from './components/AuthModal'
import { RestTimerHud } from './components/RestTimerHud'
import { CommandPalette } from './components/CommandPalette'
import type { Routine } from './types'

const AppContent: React.FC = () => {
  const { user, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [prefilledRoutine, setPrefilledRoutine] = useState<Routine | null>(null)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem' }}>
        <div className="spinner" style={{ width: '44px', height: '44px' }} />
        <p style={{ color: 'var(--text-dim)', fontSize: '0.875rem', fontWeight: 600 }}>Loading Titan Strength...</p>
      </div>
    )
  }

  if (!user) {
    return <AuthModal />
  }

  const handleStartRoutine = (routine: Routine) => {
    setPrefilledRoutine(routine)
    setActiveTab('logger')
  }

  const handleWorkoutSaved = () => {
    setPrefilledRoutine(null)
    setActiveTab('history')
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      <main style={{ flex: 1, paddingBottom: '5rem' }}>
        {activeTab === 'dashboard' && (
          <Dashboard
            onNavigateToLogger={() => setActiveTab('logger')}
            onNavigateToMealPlan={() => setActiveTab('mealplan')}
          />
        )}
        {activeTab === 'logger' && (
          <WorkoutLogger
            prefilledRoutine={prefilledRoutine}
            onWorkoutSaved={handleWorkoutSaved}
          />
        )}
        {activeTab === 'routines' && (
          <RoutinesManager onStartRoutine={handleStartRoutine} />
        )}
        {activeTab === 'history' && <WorkoutHistory />}
        {activeTab === 'analytics' && <StrengthAnalytics />}
        {activeTab === 'nutrition' && <NutritionPlanner />}
        {activeTab === 'mealplan' && <MealPlanView />}
        {activeTab === 'exercises' && <ExercisesCatalogue />}
        {activeTab === 'profile' && <ProfileSettings />}
      </main>

      {/* Global Interactive Rest Recovery Timer HUD */}
      <RestTimerHud />

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={setActiveTab}
      />
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
