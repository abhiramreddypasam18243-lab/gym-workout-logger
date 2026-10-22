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

export interface CustomFoodInput {
  name: string
  serving_description: string
  default_serving_g: string | null
  state: 'raw' | 'cooked' | 'as_sold'
  nutrients: { energy_kcal: string; protein_g: string; carbs_g: string; fat_g: string; fiber_g?: string }
  allergens: string[]
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

  // Catalogue (AC-29, AC-30, AC-49, AC-53)
  async getExercises(params?: { q?: string; muscle?: string; equipment?: string }): Promise<Exercise[]> {
    const query = new URLSearchParams()
    if (params?.q) query.set('q', params.q)
    if (params?.muscle) query.set('muscle', params.muscle)
    if (params?.equipment) query.set('equipment', params.equipment)
    const qs = query.toString() ? `?${query.toString()}` : ''
    return request<Exercise[]>(`/api/exercises${qs}`)
  },

  async createExercise(exercise: {
    name: string
    primary_muscle: string
    secondary_muscles?: string[]
    equipment: string
    instructions?: string
  }): Promise<Exercise> {
    return request<Exercise>('/api/exercises', {
      method: 'POST',
      body: JSON.stringify(exercise),
    })
  },

  async listFoods(params?: { q?: string; category?: string; limit?: number; offset?: number }): Promise<any[]> {
    const query = new URLSearchParams()
    if (params?.q) query.set('q', params.q)
    if (params?.category) query.set('category', params.category)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    const qs = query.toString() ? `?${query.toString()}` : ''
    return request<any[]>(`/api/foods${qs}`)
  },

  // Custom foods (D-32): per-100 g values the user enters; only the owner sees them
  async listMyFoods(): Promise<any[]> {
    return request<any[]>('/api/foods?mine=true&limit=100')
  },

  async createCustomFood(food: CustomFoodInput): Promise<any> {
    return request<any>('/api/foods', { method: 'POST', body: JSON.stringify(food) })
  },

  async updateCustomFood(id: string, food: Partial<CustomFoodInput>): Promise<any> {
    return request<any>(`/api/foods/${id}`, { method: 'PATCH', body: JSON.stringify(food) })
  },

  async deleteCustomFood(id: string): Promise<void> {
    await request<void>(`/api/foods/${id}`, { method: 'DELETE' })
  },

  async searchFoods(params?: { q?: string; category?: string; page?: number; page_size?: number }): Promise<{ items: any[] }> {
    const limit = params?.page_size || 50
    const offset = ((params?.page || 1) - 1) * limit
    const items = await this.listFoods({ q: params?.q, category: params?.category, limit, offset })
    return { items }
  },

  async listRecipes(params?: {
    q?: string
    cuisine?: string
    diet_tag?: string
    meal_type?: string
    max_time?: number
    page?: number
    page_size?: number
  }): Promise<{ items: any[] }> {
    const query = new URLSearchParams()
    if (params?.q) query.set('q', params.q)
    if (params?.cuisine) query.set('cuisine', params.cuisine)
    if (params?.diet_tag) query.set('diet_tag', params.diet_tag)
    if (params?.meal_type) query.set('meal_type', params.meal_type)
    if (params?.max_time) query.set('max_time', String(params.max_time))
    const limit = params?.page_size || 50
    const offset = ((params?.page || 1) - 1) * limit
    query.set('limit', String(limit))
    query.set('offset', String(offset))
    const qs = query.toString() ? `?${query.toString()}` : ''
    const items = await request<any[]>(`/api/recipes${qs}`)
    return { items }
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
  // Progressive overload hint from the last session (D-33)
  async getNextLoad(exerciseId: string, repMin?: number, repMax?: number): Promise<any> {
    const query = new URLSearchParams()
    if (repMin) query.set('rep_min', String(repMin))
    if (repMax) query.set('rep_max', String(repMax))
    const qs = query.toString() ? `?${query.toString()}` : ''
    return request<any>(`/api/analytics/next-load/${exerciseId}${qs}`)
  },

  // Working sets per muscle this week against targets (D-34)
  async getWeeklyVolume(): Promise<{ week_start: string; week_end: string; muscles: any[] }> {
    return request<any>('/api/analytics/weekly-volume')
  },

  async putWeeklyVolumeTargets(targets: Record<string, number>): Promise<{ targets: Record<string, number> }> {
    return request<any>('/api/analytics/weekly-volume/targets', { method: 'PUT', body: JSON.stringify({ targets }) })
  },

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

  // Nutrition & Targets (AC-17 to AC-28)
  async estimateNutrition(params: any): Promise<any> {
    return request<any>('/api/nutrition/goals/estimate', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  async createNutritionGoal(goal: any): Promise<any> {
    return request<any>('/api/nutrition/goals', {
      method: 'POST',
      body: JSON.stringify(goal),
    })
  },

  async getActiveNutritionGoal(onDate?: string): Promise<any> {
    const qs = onDate ? `?on_date=${onDate}` : ''
    return request<any>(`/api/nutrition/goals${qs}`)
  },

  async getNutritionPreferences(): Promise<any> {
    return request<any>('/api/nutrition/preferences')
  },

  async updateNutritionPreferences(prefs: any): Promise<any> {
    return request<any>('/api/nutrition/preferences', {
      method: 'PATCH',
      body: JSON.stringify(prefs),
    })
  },

  // Meal Planning (AC-56 to AC-72)
  async generateMealPlan(payload: {
    start_date: string
    days?: number
    meal_slots?: string[]
    max_minutes?: number
    daily_budget_minor?: number
  }): Promise<any> {
    return request<any>('/api/meal-plans/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listMealPlans(): Promise<any[]> {
    return request<any[]>('/api/meal-plans')
  },

  async getMealPlan(id: string): Promise<any> {
    return request<any>(`/api/meal-plans/${id}`)
  },

  async deleteMealPlan(id: string): Promise<void> {
    return request<void>(`/api/meal-plans/${id}`, {
      method: 'DELETE',
    })
  },

  // Substitutions & Manual Edits & Grocery List (AC-73 to AC-81)
  async suggestSubstitutions(planId: string, mealId: string): Promise<any[]> {
    return request<any[]>(`/api/meal-plans/${planId}/substitutions/suggest`, {
      method: 'POST',
      body: JSON.stringify({ meal_id: mealId }),
    })
  },

  async acceptSubstitution(
    planId: string,
    mealId: string,
    recipeId: string,
    servings: number = 1.0,
  ): Promise<any> {
    return request<any>(`/api/meal-plans/${planId}/substitutions/accept`, {
      method: 'POST',
      body: JSON.stringify({ meal_id: mealId, recipe_id: recipeId, servings }),
    })
  },

  async editPlannedMeal(
    planId: string,
    mealId: string,
    payload: { servings?: number; recipe_id?: string },
  ): Promise<any> {
    return request<any>(`/api/meal-plans/${planId}/meals/${mealId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async getGroceryList(
    planId: string,
    fromDate?: string,
    toDate?: string,
  ): Promise<any> {
    const params = new URLSearchParams()
    if (fromDate) params.set('from_date', fromDate)
    if (toDate) params.set('to_date', toDate)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return request<any>(`/api/meal-plans/${planId}/grocery-list${qs}`)
  },

  // Nutrition Logs & Intake Logging (AC-82 to AC-84)
  async listNutritionLogs(fromDate?: string, toDate?: string): Promise<any[]> {
    const params = new URLSearchParams()
    if (fromDate) params.set('from_date', fromDate)
    if (toDate) params.set('to_date', toDate)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return request<any[]>(`/api/nutrition/logs${qs}`)
  },

  async createNutritionLog(payload: {
    consumed_at: string
    meal_type: string
    notes?: string
    items: Array<{
      food_id?: string
      recipe_id?: string
      quantity: number
      unit: string
      notes?: string
    }>
  }): Promise<any> {
    return request<any>('/api/nutrition/logs', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async deleteNutritionLog(id: string): Promise<void> {
    return request<void>(`/api/nutrition/logs/${id}`, {
      method: 'DELETE',
    })
  },

  async getNutritionAnalytics(startDate: string, endDate: string): Promise<any> {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    })
    return request<any>(`/api/analytics/nutrition?${params.toString()}`)
  },

  async getDashboard(): Promise<any> {
    return request<any>('/api/dashboard')
  },

  async getInsights(window: 'last_4_weeks' | 'last_12_weeks' = 'last_4_weeks'): Promise<any> {
    return request<any>(`/api/insights?window=${window}`)
  },

  // Data Controls & Privacy (AC-88, AC-89)
  async exportData(): Promise<any> {
    const data = await request<any>('/api/export')
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `user-data-export-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
    return data
  },

  async deleteAccount(password: string): Promise<any> {
    const res = await request<any>('/api/account', {
      method: 'DELETE',
      body: JSON.stringify({ password }),
    })
    setCsrfToken(null)
    return res
  },
}

export const apiClient = api


