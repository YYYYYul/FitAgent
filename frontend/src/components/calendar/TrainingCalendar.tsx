'use client'

import { useState, useEffect } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { historyApi, planApi } from '@/lib/api'
import type { MonthlySummary, WorkoutLog, DailySchedule } from '@/lib/types'

interface TrainingCalendarProps {
  userId: string
}

const DAY_MAP_CN: Record<string, number> = {
  Monday: 1, Tuesday: 2, Wednesday: 3, Thursday: 4, Friday: 5, Saturday: 6, Sunday: 0,
}

export default function TrainingCalendar({ userId }: TrainingCalendarProps) {
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [currentDate, setCurrentDate] = useState(new Date())
  const [planSchedule, setPlanSchedule] = useState<DailySchedule[]>([])

  useEffect(() => {
    loadMonthData(currentDate.getFullYear(), currentDate.getMonth() + 1)
    loadPlanSchedule()
  }, [userId, currentDate])

  const loadMonthData = async (year: number, month: number) => {
    try {
      const data = await historyApi.monthlySummary(userId, year, month)
      setSummary(data as MonthlySummary)
    } catch {
      // Calendar will show empty
    }
  }

  const loadPlanSchedule = async () => {
    try {
      const plan = await planApi.getActive(userId) as { plan_data?: { weekly_schedule: DailySchedule[] } } | null
      if (plan?.plan_data?.weekly_schedule) {
        setPlanSchedule(plan.plan_data.weekly_schedule)
      }
    } catch {
      setPlanSchedule([])
    }
  }

  // Build events: completed workouts (green) + planned days (grey)
  const completedEvents = (summary?.daily_logs || []).map((log) => ({
    title: log.focus || '训练',
    date: log.date,
    backgroundColor: '#22c55e',
    borderColor: '#16a34a',
    textColor: '#fff',
    classNames: ['completed-workout'],
    extendedProps: {
      duration: log.duration_min,
      rpe: log.rpe,
    },
  }))

  // Generate planned-day markers for the visible month
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth() // 0-based
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const plannedEvents: { title: string; date: string; backgroundColor: string; borderColor: string; textColor: string; classNames: string[] }[] = []

  for (let d = 1; d <= daysInMonth; d++) {
    const dateObj = new Date(year, month, d)
    const dow = dateObj.getDay() // 0=Sun
    const matchedDay = planSchedule.find((s) => DAY_MAP_CN[s.day] === dow)
    if (matchedDay) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      // Skip days that already have a completed workout
      const alreadyDone = (summary?.daily_logs || []).some((l) => l.date === dateStr)
      if (!alreadyDone) {
        plannedEvents.push({
          title: `📋 ${matchedDay.focus}`,
          date: dateStr,
          backgroundColor: '#f1f5f9',
          borderColor: '#cbd5e1',
          textColor: '#64748b',
          classNames: ['planned-day'],
        })
      }
    }
  }

  const allEvents = [...completedEvents, ...plannedEvents]

  return (
    <div className="p-4">
      {/* Legend */}
      <div className="flex items-center gap-4 mb-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> 已完成
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-slate-200 border border-slate-300 inline-block" /> 计划中
        </span>
      </div>

      {/* Stats cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-xl border p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{summary.completed_days}</div>
            <div className="text-xs text-gray-500">本月训练天数</div>
          </div>
          <div className="bg-white rounded-xl border p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">{Math.round(summary.completion_rate * 100)}%</div>
            <div className="text-xs text-gray-500">完成率</div>
          </div>
          <div className="bg-white rounded-xl border p-4 text-center">
            <div className="text-2xl font-bold text-orange-600">{summary.streak_days}</div>
            <div className="text-xs text-gray-500">连续训练天数</div>
          </div>
          <div className="bg-white rounded-xl border p-4 text-center">
            <div className="text-2xl font-bold text-purple-600">{summary.total_duration_min}</div>
            <div className="text-xs text-gray-500">总时长(分钟)</div>
          </div>
        </div>
      )}

      {/* Calendar */}
      <div className="bg-white rounded-xl border p-4">
        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          locale="zh-cn"
          height="auto"
          events={allEvents}
          headerToolbar={{
            left: 'prev',
            center: 'title',
            right: 'next',
          }}
          buttonText={{ today: '今天' }}
        />
      </div>

      {/* Focus distribution */}
      {summary && Object.keys(summary.by_focus).length > 0 && (
        <div className="mt-6 bg-white rounded-xl border p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">本月部位分布</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.by_focus).map(([focus, count]) => (
              <span
                key={focus}
                className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium"
              >
                {focus}: {count}次
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
