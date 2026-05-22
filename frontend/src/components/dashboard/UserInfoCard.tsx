'use client'

import { useState } from 'react'
import { userApi } from '@/lib/api'
import type { UserProfile } from '@/lib/types'

interface UserInfoCardProps {
  user: UserProfile
  onUpdate: (user: UserProfile) => void
}

const GOAL_LABELS: Record<string, string> = {
  fat_loss: '减脂',
  muscle_gain: '增肌',
  health: '健康维持',
}
const LOCATION_LABELS: Record<string, string> = {
  home: '在家',
  gym: '健身房',
}
const EXPERIENCE_LABELS: Record<string, string> = {
  beginner: '新手',
  intermediate: '中级',
  advanced: '高级',
}

export default function UserInfoCard({ user, onUpdate }: UserInfoCardProps) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    display_name: user.display_name || '',
    height_cm: user.height_cm || '',
    weight_kg: user.weight_kg || '',
    goal: user.goal || 'health',
    training_location: user.training_location || 'home',
    weekly_days: user.weekly_days || 3,
    experience_level: user.experience_level || 'beginner',
    preferred_time: user.preferred_time || '19:00',
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await userApi.updateProfile(user.id, form) as UserProfile
      onUpdate(updated)
      setEditing(false)
    } catch (e) {
      alert('保存失败')
    }
    setSaving(false)
  }

  if (!editing) {
    return (
      <div className="bg-white rounded-xl border p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">{user.display_name || user.email}</h3>
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            编辑
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-gray-500">身高：{user.height_cm ? `${user.height_cm}cm` : '未设置'}</div>
          <div className="text-gray-500">体重：{user.weight_kg ? `${user.weight_kg}kg` : '未设置'}</div>
          <div className="text-gray-500">目标：{GOAL_LABELS[user.goal || ''] || '未设置'}</div>
          <div className="text-gray-500">地点：{LOCATION_LABELS[user.training_location || ''] || '未设置'}</div>
          <div className="text-gray-500">每周：{user.weekly_days ? `${user.weekly_days}天` : '未设置'}</div>
          <div className="text-gray-500">水平：{EXPERIENCE_LABELS[user.experience_level || ''] || '未设置'}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="font-semibold text-gray-900 mb-4">编辑个人信息</h3>
      <div className="space-y-3">
        <div>
          <label className="text-xs text-gray-500">昵称</label>
          <input
            type="text"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500">身高(cm)</label>
            <input
              type="number"
              value={form.height_cm}
              onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
              placeholder="175"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">体重(kg)</label>
            <input
              type="number"
              value={form.weight_kg}
              onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
              placeholder="70"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500">目标</label>
          <select
            value={form.goal}
            onChange={(e) => setForm({ ...form, goal: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
          >
            <option value="fat_loss">减脂</option>
            <option value="muscle_gain">增肌</option>
            <option value="health">健康维持</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">训练地点</label>
          <select
            value={form.training_location}
            onChange={(e) => setForm({ ...form, training_location: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
          >
            <option value="home">在家</option>
            <option value="gym">健身房</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">每周训练天数</label>
          <select
            value={form.weekly_days}
            onChange={(e) => setForm({ ...form, weekly_days: Number(e.target.value) })}
            className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
          >
            {[1, 2, 3, 4, 5, 6, 7].map((d) => (
              <option key={d} value={d}>{d}天</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">训练经验</label>
          <select
            value={form.experience_level}
            onChange={(e) => setForm({ ...form, experience_level: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
          >
            <option value="beginner">新手</option>
            <option value="intermediate">中级</option>
            <option value="advanced">高级</option>
          </select>
        </div>
      </div>
      <div className="flex gap-2 mt-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存'}
        </button>
        <button
          onClick={() => setEditing(false)}
          className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          取消
        </button>
      </div>
    </div>
  )
}
