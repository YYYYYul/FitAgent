'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import ChatBubble from './ChatBubble'
import ChatInput from './ChatInput'
import ConfirmationModal from './ConfirmationModal'
import { chatStream, chatConfirmStream } from '@/lib/api'
import type { ChatMessage, AgentTraceSummary, ConfirmationData } from '@/lib/types'

interface ChatContainerProps {
  userId: string
}

export default function ChatContainer({ userId }: ChatContainerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 'welcome',
      role: 'assistant',
      content: '你好！我是 FitAgent，你的专属健身助手。\n\n我可以帮你：\n• 制定个性化训练计划\n• 记录每日训练内容\n• 查看训练历史和月度复盘\n• 回答健身相关问题\n\n请先在右上角完善你的身体信息，然后告诉我你的目标吧！',
      timestamp: new Date().toISOString(),
    },
  ])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // ---- HITL Confirmation state (Phase 2C Step 2b) ----
  const [pendingConfirmation, setPendingConfirmation] = useState<ConfirmationData | null>(null)
  const [confirmationLoading, setConfirmationLoading] = useState(false)
  const assistantIdRef = useRef<string | null>(null) // track current assistant message

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ---- Normal message send ----
  const handleSend = useCallback(
    (text: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])

      const assistantId = crypto.randomUUID()
      assistantIdRef.current = assistantId
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])

      setIsStreaming(true)

      abortRef.current = chatStream(
        userId, text, sessionId,
        (event) => handleSSEEvent(event, assistantId),
        (error) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: `连接错误：${error.message}` } : m))
          )
          setIsStreaming(false)
        },
        () => {
          setIsStreaming(false)
        }
      )
    },
    [userId, sessionId]
  )

  // ---- Shared SSE event handler (used by normal chat AND confirmation resume) ----
  const handleSSEEvent = useCallback(
    (event: { type: string; content: string; data?: Record<string, unknown> }, assistantId: string) => {
      if (event.type === 'thinking') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId && !m.content ? { ...m, content: event.content } : m
          )
        )
      } else if (event.type === 'intent') {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, intent: event.content as string } : m))
        )
      } else if (event.type === 'text') {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: event.content as string } : m))
        )
      } else if (event.type === 'trace') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, trace: event.data as unknown as AgentTraceSummary } : m
          )
        )
      } else if (event.type === 'tool_call') {
        // Tool call events don't change the visible message; trace captures them
      } else if (event.type === 'error') {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: `错误：${event.content}` } : m))
        )
      }

      // ---- HITL: confirmation_required (Phase 2C Step 2b) ----
      else if (event.type === 'confirmation_required') {
        // Pause the chat: set pending confirmation for modal display
        const cData = event.data as unknown as ConfirmationData
        if (cData) {
          setPendingConfirmation(cData)
          // Remove the placeholder message (confirmation is rendered by the modal, not chat)
          setMessages((prev) => prev.filter((m) => m.id !== assistantId))
        }
        setIsStreaming(false)
      }
    },
    []
  )

  // ---- HITL: User clicks Confirm ----
  const handleConfirm = useCallback(async () => {
    if (!pendingConfirmation) return

    setConfirmationLoading(true)
    const confSessionId = pendingConfirmation.session_id

    // Add a system message showing the confirmation result
    const assistantId = crypto.randomUUID()
    assistantIdRef.current = assistantId
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'system', content: '已确认重新生成训练计划', timestamp: new Date().toISOString() },
      { id: assistantId, role: 'assistant', content: '', timestamp: new Date().toISOString() },
    ])

    // Clear confirmation state
    setPendingConfirmation(null)
    setIsStreaming(true)

    // Resume SSE stream via /chat/confirm
    abortRef.current = chatConfirmStream(
      confSessionId,
      (event) => handleSSEEvent(event, assistantId),
      (error) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: `确认处理错误：${error.message}` } : m))
        )
        setIsStreaming(false)
        setConfirmationLoading(false)
      },
      () => {
        setIsStreaming(false)
        setConfirmationLoading(false)
      }
    )
  }, [pendingConfirmation, handleSSEEvent])

  // ---- HITL: User clicks Cancel ----
  const handleCancel = useCallback(async () => {
    if (!pendingConfirmation) return

    const confSessionId = pendingConfirmation.session_id
    setPendingConfirmation(null)

    // Send cancel to backend
    try {
      await fetch('http://localhost:8001/api/v1/chat/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: confSessionId, confirmed: false }),
      })
    } catch {
      // ignore network errors on cancel
    }

    // Show cancel message
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'system', content: '操作已取消。你的当前训练计划保持不变。', timestamp: new Date().toISOString() },
      { id: crypto.randomUUID(), role: 'assistant', content: '好的，当前训练计划保持不变。请问还有什么需要帮助的吗？', timestamp: new Date().toISOString() },
    ])
  }, [pendingConfirmation])

  // Determine if chat input should be disabled
  const inputDisabled = isStreaming || pendingConfirmation !== null

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {isStreaming && (
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-4">
              <span className="animate-pulse">&#x25CF;</span>
              <span>思考中...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <ChatInput
        onSend={handleSend}
        disabled={inputDisabled}
        placeholder={pendingConfirmation ? '请先确认当前操作...' : undefined}
      />

      {/* HITL Confirmation Modal (Phase 2C Step 2b) */}
      {pendingConfirmation && (
        <ConfirmationModal
          data={pendingConfirmation}
          loading={confirmationLoading}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}
    </div>
  )
}
