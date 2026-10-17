import type {
  Exercise,
  Routine,
  UserProfile,
  WorkoutHistoryResponse,
  WorkoutSession,
  WorkoutSessionCreate,
} from '../types'

let cachedCsrfToken: string | null = null

export function setCsrfToken(token: string | null) {
  cachedCsrfToken = token
  if (token) {
    try {
      localStorage.setItem('csrf_token', token)
    } catch {
      // ignore in environments without localStorage
    }
  } else {
    try {
      localStorage.removeItem('csrf_token')
    } catch {
      // ignore
    }
  }
}

export function getCsrfToken(): string | null {
  if (cachedCsrfToken) return cachedCsrfToken

  try {
    const stored = localStorage.getItem('csrf_token')
    if (stored) {
      cachedCsrfToken = stored
      return stored
    }
  } catch {
    // ignore
  }

  // Parse from document.cookie
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/csrf_token=([^;]+)/)
    if (match && match[1]) {
      cachedCsrfToken = decodeURIComponent(match[1])
      return cachedCsrfToken
    }
  }

  return null
}

export class ApiError extends Error {
  code: string
  status: number
  details?: Record<string, unknown>

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'application/json')

  const method = (options.method || 'GET').toUpperCase()
  if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken()
    if (csrf) {
      headers.set('X-CSRF-Token', csrf)
    }
    if (!headers.has('Content-Type') && options.body) {
      headers.set('Content-Type', 'application/json')
    }
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'include',
  })

  // Read response
  let data: any = null
  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    const errorDetail = data?.detail || data?.error || {}
    const code = errorDetail.code || `HTTP_${response.status}`
    const message = errorDetail.message || data?.message || response.statusText || 'Request failed'
    throw new ApiError(response.status, code, message, errorDetail)
  }

  return data as T
}

export const api = {
  // Auth
  async register(email: string, password: string, displayName?: string) {
    return request<{ user: any }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
  },

  async login(email: string, password: string) {
    const res = await request<{ user: any; csrf_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    if (res.csrf_token) {
      setCsrfToken(res.csrf_token)
    }
    return res
  },

  async logout() {
    try {
      await request('/api/auth/logout', { method: 'POST' })
    } finally {
      setCsrfToken(null)
    }
  },

  async getMe() {
    return request<{ user: any }>('/api/auth/me')
  },

  // Profile
  async getProfile(): Promise<UserProfile> {
    return request<UserProfile>('/api/profile')
  },

  async updateProfile(updates: Partial<UserProfile>): Promise<UserProfile> {
    return request<UserProfile>('/api/profile', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  },

  async confirmAdult(): Promise<{ adult_confirmed_at: string }> {
    return request<{ adult_confirmed_at: string }>('/api/profile/confirm-adult', {
      method: 'POST',
    })
  },

  // Catalogue
  async getExercises(params?: { q?: string; muscle?: string; equipment?: string }): Promise<Exercise[]> {
    const query = new URLSearchParams()
    if (params?.q) query.set('q', params.q)
    if (params?.muscle) query.set('muscle', params.muscle)
    if (params?.equipment) query.set('equipment', params.equipment)
    const qs = query.toString() ? `?${query.toString()}` : ''
    return request<Exercise[]>(`/api/catalogue/exercises${qs}`)
  },

  async createExercise(exercise: {
    name: string
    primary_muscle: string
    secondary_muscles?: string[]
    equipment: string
    instructions?: string
  }): Promise<Exercise> {
    return request<Exercise>('/api/catalogue/exercises', {
      method: 'POST',
      body: JSON.stringify(exercise),
    })
  },

  // Routines
  async getRoutines(): Promise<Routine[]> {
    return request<Routine[]>('/api/routines')
  },

  async createRoutine(routine: {
    name: string
    description?: string
    exercises: {
      exercise_id: string
      order_in_routine: number
      target_sets: number
      rep_min: number
      rep_max: number
      notes?: string
    }[]
  }): Promise<Routine> {
    return request<Routine>('/api/routines', {
      method: 'POST',
      body: JSON.stringify(routine),
    })
  },

  async duplicateRoutine(id: string): Promise<Routine> {
    return request<Routine>(`/api/routines/${id}/duplicate`, {
      method: 'POST',
    })
  },

  async deleteRoutine(id: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/api/routines/${id}`, {
      method: 'DELETE',
    })
  },

  async startRoutine(id: string): Promise<any> {
    return request<any>(`/api/routines/${id}/start`, {
      method: 'POST',
    })
  },

  // Workouts
  async getWorkouts(cursor?: string, limit = 20): Promise<WorkoutHistoryResponse> {
    const query = new URLSearchParams({ limit: limit.toString() })
    if (cursor) query.set('cursor', cursor)
    return request<WorkoutHistoryResponse>(`/api/workouts?${query.toString()}`)
  },

  async getWorkout(id: string): Promise<WorkoutSession> {
    return request<WorkoutSession>(`/api/workouts/${id}`)
  },

  async createWorkout(workout: WorkoutSessionCreate): Promise<WorkoutSession> {
    return request<WorkoutSession>('/api/workouts', {
      method: 'POST',
      body: JSON.stringify(workout),
    })
  },

  async updateWorkout(id: string, workout: WorkoutSessionCreate): Promise<WorkoutSession> {
    return request<WorkoutSession>(`/api/workouts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(workout),
    })
  },

  async deleteWorkout(id: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/api/workouts/${id}`, {
      method: 'DELETE',
    })
  },

  // Strength Analytics (AC-39 to AC-44)
  async getStrengthTrends(exerciseId: string, days?: number): Promise<any[]> {
    const query = new URLSearchParams({ exercise_id: exerciseId })
    if (days) query.set('days', days.toString())
    return request<any[]>(`/api/analytics/strength?${query.toString()}`)
  },

  async getWeeklyConsistency(weeks = 12): Promise<{ weekly_target: number; weeks: any[] }> {
    return request<{ weekly_target: number; weeks: any[] }>(`/api/analytics/consistency?weeks=${weeks}`)
  },

  async getExercisePrs(exerciseId: string): Promise<any[]> {
    return request<any[]>(`/api/analytics/prs/${exerciseId}`)
  },
}
