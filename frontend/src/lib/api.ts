const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// SSE Chat stream
export function chatStream(
  user_id: string,
  message: string,
  session_id: string,
  onEvent: (event: { type: string; content: string; data?: Record<string, unknown> }) => void,
  onError: (error: Error) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController()

  fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, message, session_id }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onEvent(data)
              if (data.type === 'done') {
                onDone()
                return
              }
            } catch {
              // skip parse errors
            }
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err)
      }
    })

  return controller
}

// User APIs
export const userApi = {
  register: (email: string, password: string, display_name?: string) =>
    apiFetch('/user/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name }),
    }),
  login: (email: string, password: string) =>
    apiFetch('/user/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getProfile: (userId: string) => apiFetch(`/user/${userId}`),
  updateProfile: (userId: string, data: Record<string, unknown>) =>
    apiFetch(`/user/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}

// Plan APIs
export const planApi = {
  generate: (data: Record<string, unknown>) =>
    apiFetch('/plan/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  save: (userId: string, data: Record<string, unknown>) =>
    apiFetch(`/plan/save/${userId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getActive: (userId: string) => apiFetch(`/plan/active/${userId}`),
  getHistory: (userId: string) => apiFetch(`/plan/history/${userId}`),
}

// HITL Confirmation (Phase 2C Step 2)
export async function chatConfirm(
  session_id: string,
  confirmed: boolean,
): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/chat/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, confirmed }),
  })
  if (res.status === 404) {
    throw new Error('没有待确认的操作，可能已超时或已被处理。')
  }
  if (res.status === 410) {
    throw new Error('确认已超时，操作自动取消。请重新发起请求。')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  // For cancel (confirmed=false), return JSON
  // For confirm (confirmed=true), the response is SSE — handled separately
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return res.json()
  }
  return { status: 'ok', message: '' }
}

// HITL: confirm and resume SSE stream
export function chatConfirmStream(
  session_id: string,
  onEvent: (event: { type: string; content: string; data?: Record<string, unknown> }) => void,
  onError: (error: Error) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController()

  fetch(`${API_BASE}/chat/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, confirmed: true }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(err.detail || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onEvent(data)
              if (data.type === 'done') {
                onDone()
                return
              }
            } catch {
              // skip parse errors
            }
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err)
      }
    })

  return controller
}

// History APIs
export const historyApi = {
  logWorkout: (userId: string, raw_text: string, date?: string) =>
    apiFetch(`/history/log/${userId}`, {
      method: 'POST',
      body: JSON.stringify({ raw_text, date }),
    }),
  getLogs: (userId: string, year?: number, month?: number) => {
    const params = new URLSearchParams()
    if (year) params.set('year', String(year))
    if (month) params.set('month', String(month))
    return apiFetch(`/history/logs/${userId}?${params}`)
  },
  monthlySummary: (userId: string, year: number, month: number) =>
    apiFetch(`/history/monthly-summary/${userId}?year=${year}&month=${month}`),
}
