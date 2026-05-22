'use client'

/**
 * ConfirmationModal — minimal HITL confirmation dialog (Phase 2C Step 2b).
 *
 * Renders when the backend sends a "confirmation_required" SSE event.
 * The user must explicitly confirm or cancel before the Agent continues.
 *
 * WHY a simple modal over the chat area:
 *   - Keeps chat context visible behind the overlay
 *   - Prevents background interactions during confirmation
 *   - No complex state management needed
 */

import type { ConfirmationData } from '@/lib/types'

interface ConfirmationModalProps {
  data: ConfirmationData
  loading: boolean
  onConfirm: () => void
  onCancel: () => void
}

const IMPACT_LABELS: Record<string, { label: string; color: string }> = {
  high: { label: '高影响', color: 'text-red-600 bg-red-50' },
  medium: { label: '中影响', color: 'text-yellow-600 bg-yellow-50' },
  low: { label: '低影响', color: 'text-blue-600 bg-blue-50' },
}

export default function ConfirmationModal({
  data,
  loading,
  onConfirm,
  onCancel,
}: ConfirmationModalProps) {
  const impact = IMPACT_LABELS[data.impact] || IMPACT_LABELS.medium

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl shrink-0">&#x26A0;&#xFE0F;</span>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900">{data.title}</h3>
              <span className={`inline-block text-xs px-2 py-0.5 rounded-full mt-1 ${impact.color}`}>
                {impact.label}
              </span>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">{data.description}</p>
        </div>

        {/* Actions */}
        <div className="px-6 pb-6 flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '处理中...' : '确认'}
          </button>
        </div>
      </div>
    </div>
  )
}
