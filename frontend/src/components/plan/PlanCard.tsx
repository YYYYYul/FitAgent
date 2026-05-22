'use client'

import { useState, useEffect } from 'react'
import { planApi } from '@/lib/api'
import type { TrainingPlan } from '@/lib/types'

interface PlanCardProps {
  userId: string
}

const DAY_LABELS: Record<string, string> = {
  Monday: '周一', Tuesday: '周二', Wednesday: '周三',
  Thursday: '周四', Friday: '周五', Saturday: '周六', Sunday: '周日',
}

export default function PlanCard({ userId }: PlanCardProps) {
  const [plan, setPlan] = useState<TrainingPlan | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPlan()
  }, [userId])

  const loadPlan = async () => {
    try {
      const data = await planApi.getActive(userId)
      setPlan(data as TrainingPlan | null)
    } catch {
      // No plan yet
    }
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl border p-5">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 rounded w-1/3" />
          <div className="h-3 bg-gray-200 rounded w-2/3" />
        </div>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="bg-white rounded-xl border p-5">
        <h3 className="font-semibold text-gray-900 mb-2">训练计划</h3>
        <p className="text-sm text-gray-500">还没有训练计划，在聊天中告诉我你的目标来生成一个吧！</p>
        <p className="text-xs text-gray-400 mt-1">例如：「帮我制定一个减脂训练计划」</p>
      </div>
    )
  }

  const schedule = plan.plan_data?.weekly_schedule || []

  return (
    <div className="bg-white rounded-xl border p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">
          训练计划
          <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${plan.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-500'}`}>
            {plan.status === 'active' ? '进行中' : plan.status}
          </span>
        </h3>
      </div>
      {plan.plan_summary && (
        <p className="text-sm text-gray-500 mb-4">{plan.plan_summary}</p>
      )}
      <div className="space-y-2">
        {schedule.slice(0, 4).map((day) => (
          <div key={day.day} className="flex items-center gap-3 text-sm border-b pb-2 last:border-0">
            <span className="text-xs text-gray-400 w-10 shrink-0">
              {DAY_LABELS[day.day] || day.day}
            </span>
            <span className="text-gray-700 font-medium">{day.focus}</span>
            <span className="text-gray-400 text-xs ml-auto">{day.total_duration_min}分钟</span>
          </div>
        ))}
      </div>
      {schedule.length > 4 && (
        <p className="text-xs text-gray-400 mt-2">还有 {schedule.length - 4} 天训练...</p>
      )}
    </div>
  )
}
