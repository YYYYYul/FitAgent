'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import TrainingCalendar from '@/components/calendar/TrainingCalendar'
import type { UserProfile } from '@/lib/types'

export default function CalendarPage() {
  const [user, setUser] = useState<UserProfile | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem('fitagent_user')
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        // not logged in
      }
    }
  }, [])

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-gray-500 mb-4">请先登录</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700 text-sm">
            返回首页登录
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">训练日历</h1>
          <Link href="/" className="text-sm text-blue-600 hover:text-blue-700">
            ← 返回对话
          </Link>
        </div>
      </header>
      <div className="max-w-5xl mx-auto py-6">
        <TrainingCalendar userId={user.id} />
      </div>
    </div>
  )
}
