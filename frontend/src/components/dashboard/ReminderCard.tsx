'use client'

import { useState, useEffect } from 'react'

interface ReminderCardProps {
  userId: string
}

interface NextReminder {
  day_label: string
  remind_time: string
  next_date: string
  days_until: number
}

interface ReminderData {
  has_next: boolean
  next_reminder?: NextReminder
  total_active: number
  scheduler_running: boolean
}

export default function ReminderCard({ userId }: ReminderCardProps) {
  const [data, setData] = useState<ReminderData | null>(null)

  useEffect(() => {
    if (!userId) return
    fetch(`http://localhost:8001/api/v1/reminders/next?user_id=${userId}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null))
  }, [userId])

  if (!data) return null

  const next = data.next_reminder

  return (
    <div className="bg-white rounded-xl border p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-1.5">
        <span>⏰</span> 提醒状态
      </h3>

      {next ? (
        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">下次提醒</span>
            <span className="text-gray-700 font-medium">{next.day_label} {next.remind_time}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">日期</span>
            <span className="text-gray-700">{next.next_date}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">距离</span>
            <span className={`font-medium ${next.days_until === 0 ? 'text-green-600' : 'text-blue-600'}`}>
              {next.days_until === 0 ? '今天' : `${next.days_until} 天后`}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">活跃提醒</span>
            <span className="text-gray-700">{data.total_active} 条</span>
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-400">暂无活跃提醒</p>
      )}

      <div className="mt-3 pt-3 border-t flex items-center gap-1.5 text-xs">
        <span className={`w-2 h-2 rounded-full ${data.scheduler_running ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-gray-400">
          {data.scheduler_running ? '调度器运行中' : '调度器未运行'}
        </span>
      </div>
    </div>
  )
}
