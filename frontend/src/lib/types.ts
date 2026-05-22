// Chat
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  intent?: string
  trace?: AgentTraceSummary
  timestamp: string
}

export interface SSEEvent {
  type: 'thinking' | 'intent' | 'plan' | 'tool_call' | 'tool_result' | 'text' | 'done' | 'error' | 'trace' | 'confirmation_required' | 'replan' | 'rag'
  content: string
  data?: Record<string, unknown>
}

// HITL Confirmation (Phase 2C Step 2)
export interface ConfirmationData {
  target: string
  title: string
  description: string
  impact: string
  session_id: string
  expires_in_seconds: number
}

export interface AgentTraceSummary {
  trace_id: string
  user_id: string
  session_id: string
  intent: string
  intent_confidence: number
  tools_called: string[]
  latency_ms: number
}

// User
export interface UserProfile {
  id: string
  email: string
  display_name?: string
  height_cm?: number
  weight_kg?: number
  goal?: string
  training_location?: string
  weekly_days?: number
  experience_level?: string
  preferred_time?: string
}

// Plan
export interface ExerciseItem {
  name: string
  sets: number
  reps: string
  rest_sec: number
  notes?: string
}

export interface DailySchedule {
  day: string
  focus: string
  warmup: string
  exercises: ExerciseItem[]
  cardio?: string
  total_duration_min: number
  cooldown?: string
}

export interface TrainingPlan {
  id: string
  status: string
  goal?: string
  weekly_days?: number
  plan_data?: {
    weekly_schedule: DailySchedule[]
  }
  plan_summary?: string
  created_at: string
}

// Workout
export interface ParsedExercise {
  name: string
  sets?: number
  reps?: number
  weight_kg?: number
  rpe?: number
}

export interface WorkoutLog {
  id: string
  date: string
  raw_text: string
  parsed_record?: {
    focus?: string
    duration_min?: number
    exercises?: ParsedExercise[]
    rpe?: number
    notes?: string
  }
  duration_min?: number
  rpe?: number
}

export interface MonthlySummary {
  year: number
  month: number
  planned_days: number
  completed_days: number
  completion_rate: number
  streak_days: number
  total_duration_min: number
  by_focus: Record<string, number>
  daily_logs: Array<{
    date: string
    focus?: string
    duration_min?: number
    rpe?: number
  }>
}
