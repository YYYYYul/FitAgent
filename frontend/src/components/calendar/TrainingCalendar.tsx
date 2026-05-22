'use client'

import { useState, useEffect } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { historyApi } from '@/lib/api'
import type { MonthlySummary, WorkoutLog } from '@/lib/types'

interface TrainingCalendarProps {
  userId: string
}

export default function TrainingCalendar({ userId }: TrainingCalendarProps) {
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [selectedLog, setSelectedLog] = useState<WorkoutLog | null>(null)
  const [currentDate, setCurrentDate] = useState(new Date())

  useEffect(() => {
    loadMonthData(currentDate.getFullYear(), currentDate.getMonth() + 1)
  }, [userId, currentDate])

  const loadMonthData = async (year: number, month: number) => {
    try {
      const data = await historyApi.monthlySummary(userId, year, month)
      setSummary(data as MonthlySummary)
    } catch {
      // Calendar will show empty
    }
  }

  const events = (summary?.daily_logs || []).map((log) => ({
    title: log.focus || '训练',
    date: log.date,
    backgroundColor: '#22c55e',
    borderColor: '#16a34a',
    textColor: '#fff',
    extendedProps: {
      duration: log.duration_min,
      rpe: log.rpe,
    },
  }))

  const handleDatesSet = (arg: { start: Date }) => {
    setCurrentDate(arg.start)
  }

  const handleEventClick = (info: { event: { title: string; startStr: string; extendedProps: Record<string, unknown> } }) => {
    setSelectedLog({
      id: '',
      date: info.event.startStr,
      raw_text: '',
      parsed_record: {
        focus: info.event.title,
        duration_min: info.event.extendedProps.duration as number,
        rpe: info.event.extendedProps.rpe as number,
      },
    })
  }

  return (
    <div className="p-4">
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
          events={events}
          datesSet={handleDatesSet}
          eventClick={handleEventClick}
          headerToolbar={{
            left: 'prev',
            center: 'title',
            right: 'next',
          }}
          buttonText={{
            today: '今天',
          }}
          dayCellClassNames="hover:bg-blue-50 cursor-pointer"
          eventClassNames="text-xs py-0.5 px-1 rounded"
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
