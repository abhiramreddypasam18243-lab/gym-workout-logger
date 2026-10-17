import React, { createContext, useEffect, useState, useCallback } from 'react'
import { api, setCsrfToken } from '../api/client'
import type { User, UserProfile, UnitType } from '../types'

interface AuthContextType {
  user: User | null
  profile: UserProfile | null
  units: UnitType
  isLoading: boolean
  error: string | null
  login: (email: string, pass: string) => Promise<void>
  register: (email: string, pass: string, name?: string) => Promise<void>
  logout: () => Promise<void>
  refreshProfile: () => Promise<void>
  confirmAdult: () => Promise<void>
  updateUnits: (units: UnitType) => Promise<void>
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshProfile = useCallback(async () => {
    try {
      const p = await api.getProfile()
      setProfile(p)
    } catch (err: any) {
      console.warn('Could not load profile:', err.message)
    }
  }, [])

  const checkAuth = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const meRes = await api.getMe()
      setUser(meRes.user)
      await refreshProfile()
    } catch {
      setUser(null)
      setProfile(null)
      setCsrfToken(null)
    } finally {
      setIsLoading(false)
    }
  }, [refreshProfile])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (email: string, pass: string) => {
    setError(null)
    const res = await api.login(email, pass)
    setUser(res.user)
    await refreshProfile()
  }

  const register = async (email: string, pass: string, name?: string) => {
    setError(null)
    await api.register(email, pass, name)
    // Log in automatically after registration
    await login(email, pass)
  }

  const logout = async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
      setProfile(null)
    }
  }

  const confirmAdult = async () => {
    await api.confirmAdult()
    await refreshProfile()
  }

  const updateUnits = async (units: UnitType) => {
    const updated = await api.updateProfile({ units })
    setProfile(updated)
  }

  const units: UnitType = profile?.units || 'kg'

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        units,
        isLoading,
        error,
        login,
        register,
        logout,
        refreshProfile,
        confirmAdult,
        updateUnits,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export { useAuth } from './useAuth'

