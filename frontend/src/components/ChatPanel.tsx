import { useState, useRef, useEffect } from 'react'
import type { ChatMessage } from '../App'

interface ChatPanelProps {
  messages: ChatMessage[]
  onSendMessage: (message: string) => void
}

export default function ChatPanel({ messages, onSendMessage }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    // Check if last message is from user (loading state)
    const lastMsg = messages[messages.length - 1]
    if (lastMsg?.role === 'user') {
      setLoading(true)
    } else {
      setLoading(false)
    }
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || loading) return
    
    onSendMessage(trimmed)
    setInput('')
    
    // Focus back to input
    setTimeout(() => inputRef.current?.focus(), 100)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-panel">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-title">Chat with Graph</div>
        <div className="chat-header-subtitle">Order to Cash</div>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="chat-message bot">
            <div className="chat-avatar bot">D</div>
            <div className="chat-bubble">
              <div className="chat-sender">
                Dodge AI <span className="chat-role">Graph Agent</span>
              </div>
              <div className="chat-loading">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-status">
          <span className="chat-status-dot" />
          Dodge AI is awaiting instructions
        </div>
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Analyze anything"
            rows={1}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            title="Send"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

function renderInlineMarkdown(text: string): string {
  // Convert **bold** to <strong>bold</strong>
  return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const [showSql, setShowSql] = useState(false)

  return (
    <div className={`chat-message ${message.role}`}>
      <div className={`chat-avatar ${message.role}`}>
        {message.role === 'bot' ? 'D' : 'Y'}
      </div>
      <div className="chat-bubble">
        <div className="chat-sender">
          {message.role === 'bot' ? (
            <>Dodge AI <span className="chat-role">Graph Agent</span></>
          ) : (
            'You'
          )}
        </div>
        <div style={{ whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: renderInlineMarkdown(message.content) }} />

        {message.sql && (
          <>
            <button
              className="chat-sql-toggle"
              onClick={() => setShowSql(prev => !prev)}
            >
              {showSql ? 'Hide SQL' : 'Show SQL query'}
            </button>
            {showSql && (
              <div className="chat-sql">{message.sql}</div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
