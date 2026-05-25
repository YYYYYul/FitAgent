'use client'

import { useState, useEffect } from 'react'
import ChatContainer from '@/components/chat/ChatContainer'
import UserInfoCard from '@/components/dashboard/UserInfoCard'
import ReminderCard from '@/components/dashboard/ReminderCard'
import PlanCard from '@/components/plan/PlanCard'
import { userApi } from '@/lib/api'
import type { UserProfile } from '@/lib/types'

export default function Home() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('demo@fitagent.dev')
  const [password, setPassword] = useState('demo123')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Check for stored token on mount
  useEffect(() => {
    const stored = localStorage.getItem('fitagent_user')
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem('fitagent_user')
      }
    }
  }, [])

  const handleAuth = async () => {
    setError('')
    setLoading(true)
    try {
      let result: Record<string, unknown>
      if (authMode === 'register') {
        result = await userApi.register(email, password, name || undefined) as Record<string, unknown>
      } else {
        result = await userApi.login(email, password) as Record<string, unknown>
      }
      const userProfile = result.user as UserProfile
      setUser(userProfile)
      localStorage.setItem('fitagent_user', JSON.stringify(userProfile))
    } catch (e) {
      setError(e instanceof Error ? e.message : '认证失败')
    }
    setLoading(false)
  }

  const handleUserUpdate = (updated: UserProfile) => {
    setUser(updated)
    localStorage.setItem('fitagent_user', JSON.stringify(updated))
  }

  // Auth screen
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-white">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">FitAgent</h1>
            <p className="text-gray-500 mt-2">你的智能健身助手</p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 mb-4">{error}</div>
          )}

          <div className="space-y-4">
            {authMode === 'register' && (
              <div>
                <label className="text-sm text-gray-600">昵称</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border rounded-lg px-4 py-2.5 mt-1 text-sm"
                  placeholder="你的名字"
                />
              </div>
            )}
            <div>
              <label className="text-sm text-gray-600">邮箱</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border rounded-lg px-4 py-2.5 mt-1 text-sm"
                placeholder="demo@fitagent.dev"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border rounded-lg px-4 py-2.5 mt-1 text-sm"
                placeholder="至少6位"
                onKeyDown={(e) => e.key === 'Enter' && handleAuth()}
              />
            </div>
            <button
              onClick={handleAuth}
              disabled={loading}
              className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? '处理中...' : authMode === 'login' ? '登录' : '注册'}
            </button>
          </div>

          <div className="text-center mt-4">
            <button
              onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {authMode === 'login' ? '没有账号？注册' : '已有账号？登录'}
            </button>
          </div>

          <p className="text-xs text-gray-400 text-center mt-6">
            Demo: demo@fitagent.dev / demo123
          </p>
        </div>
      </div>
    )
  }

  // Main app
  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-80' : 'w-0'} shrink-0 border-r bg-white transition-all duration-300 overflow-hidden`}>
        <div className="p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">FitAgent</h2>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              收起
            </button>
          </div>
          <UserInfoCard user={user} onUpdate={handleUserUpdate} />
          <PlanCard userId={user.id} />

          <ReminderCard userId={user.id} />

          {/* Navigation */}
          <a
            href="/calendar"
            className="block bg-white rounded-xl border p-4 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">📅</span>
              <span className="text-sm font-medium text-gray-700">训练日历</span>
              <span className="text-xs text-gray-400 ml-auto">→</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">查看训练记录与月度统计</p>
          </a>

          <div className="bg-white rounded-xl border p-4">
            <button
              onClick={() => {
                localStorage.removeItem('fitagent_user')
                setUser(null)
              }}
              className="text-sm text-gray-500 hover:text-red-600"
            >
              退出登录
            </button>
          </div>
        </div>
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col min-w-0">
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute top-4 left-4 z-10 bg-white border rounded-lg px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700"
          >
            展开侧栏
          </button>
        )}
        <ChatContainer userId={user.id} />
      </main>
    </div>
  )
}
