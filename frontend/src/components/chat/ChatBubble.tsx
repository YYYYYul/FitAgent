'use client'

import type { ChatMessage } from '@/lib/types'

interface ChatBubbleProps {
  message: ChatMessage
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <span className="text-xs text-gray-400 bg-gray-50 rounded-full px-3 py-1">
          {message.content}
        </span>
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-1' : 'order-1'}`}>
        {/* Role indicator */}
        <div className={`flex items-center gap-2 mb-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {!isUser && (
            <span className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs shrink-0">
              F
            </span>
          )}
          <span className="text-xs text-gray-400">{isUser ? '你' : 'FitAgent'}</span>
          {isUser && (
            <span className="w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center text-white text-xs shrink-0">
              U
            </span>
          )}
        </div>

        {/* Intent badge */}
        {!isUser && message.intent && message.intent !== 'casual_chat' && (
          <div className="mb-1">
            <span className="inline-block text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
              {message.intent}
            </span>
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-md'
              : 'bg-gray-100 text-gray-900 rounded-bl-md'
          }`}
        >
          {message.content}
        </div>

        {/* Trace info (for demos) */}
        {!isUser && message.trace && (
          <div className="mt-1 text-[10px] text-gray-400">
            intent: {message.trace.intent} | latency: {message.trace.latency_ms}ms
            {message.trace.tools_called.length > 0 && (
              <> | tools: {message.trace.tools_called.join(', ')}</>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
