import React, { useRef, useEffect } from 'react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: number;
  tool_results?: Record<string, unknown> | Array<Record<string, unknown>>;
}

interface ChatPanelProps {
  messages: Message[];
  isLoading: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isLoading,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-panel">
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Start a conversation with the AI Assistant</p>
          </div>
        )}
        {messages.map((message) => (
          <div key={message.id} className={`message message-${message.role}`}>
            <div className="message-header">
              <span className="role">{message.role === 'user' ? 'You:' : 'AI:'}</span>
            </div>
            <div className="message-separator">
              {message.role === 'user'
                ? '*-------------------'
                : '*-------------------------------------'}
            </div>
            <div className="message-content">{message.text}</div>
            {message.tool_results && Object.keys(message.tool_results).length > 0 && (
              <div className="tool-results">
                <details>
                  <summary>Tool Results</summary>
                  <pre>{JSON.stringify(message.tool_results, null, 2)}</pre>
                </details>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message message-assistant loading">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
