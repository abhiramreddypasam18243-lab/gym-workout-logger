export type UnitType = 'kg' | 'lb'

export interface User {
  id: string
  email: string
  display_name: string
  is_active: boolean
}

export interface UserProfile {
  user_id: string
  display_name: string
  birth_date: string | null
  height_cm: string | null
  body_weight_kg: string | null
  timezone: string
  units: UnitType
  sex_for_estimate: string
  adult_confirmed_at: string | null
  needs_professional_guidance: boolean
  calories_hidden: boolean
  nutrition_paused: boolean
  track_body_weight: boolean
  weekly_session_target: number
  currency_code: string
  goal: string
  activity_level: string
}

export interface Exercise {
  id: string
  name: string
  primary_muscle: string
  secondary_muscles: string[]
  equipment: string
  instructions: string | null
  is_custom: boolean
  owner_id?: string | null
}

export interface RoutineExercise {
  id?: string
  exercise_id: string
  order_in_routine: number
  target_sets: number
  rep_min: number
  rep_max: number
  notes?: string | null
  exercise?: Exercise
  exercise_name?: string | null
}

export interface Routine {
  id: string
  name: string
  description: string | null
  created_at: string
  exercises: RoutineExercise[]
}

export interface WorkoutSetInput {
  set_number: number
  reps: number
  load_kg: number
  rpe?: number | null
  is_warmup?: boolean
  notes?: string | null
  completed_at?: string | null
}

export interface WorkoutExerciseInput {
  exercise_id: string
  order_in_session: number
  notes?: string | null
  sets: WorkoutSetInput[]
}

export interface WorkoutSessionCreate {
  routine_id?: string | null
  started_at: string
  completed_at?: string | null
  notes?: string | null
  exercises: WorkoutExerciseInput[]
}

export interface WorkoutSet {
  id: string
  set_number: number
  reps: number
  load_kg: number
  rpe?: number | null
  is_warmup: boolean
  notes?: string | null
  completed_at?: string | null
}

export interface WorkoutExercise {
  id: string
  exercise_id: string
  order_in_session: number
  notes?: string | null
  exercise?: Exercise
  exercise_name?: string | null
  sets: WorkoutSet[]
}

export interface WorkoutSession {
  id: string
  routine_id?: string | null
  started_at: string
  completed_at?: string | null
  notes?: string | null
  exercises: WorkoutExercise[]
}

export interface WorkoutHistoryResponse {
  items: WorkoutSession[]
  next_cursor: string | null
  total_count?: number
}
