import React, { useState } from 'react'
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
import type { Routine } from './types'

const AppContent: React.FC = () => {
  const { user, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [prefilledRoutine, setPrefilledRoutine] = useState<Routine | null>(null)

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem' }}>
        <div className="spinner" style={{ width: '40px', height: '40px' }} />
        <p style={{ color: 'var(--text-dim)', fontSize: '0.875rem' }}>Loading Titan Strength...</p>
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
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-main)' }}>
      <Navbar activeTab={activeTab} onSelectTab={setActiveTab} />

      <main style={{ flex: 1, paddingBottom: '3rem' }}>
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
