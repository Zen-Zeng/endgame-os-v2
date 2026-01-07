/**
 * 对话页面
 * 按照原型图 Layout 4-5 设计
 */
import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, RefreshCw } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';
import { api } from '../lib/api';
import clsx from 'clsx';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function ChatPage() {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 发送消息
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // 添加空的 AI 消息占位
    const aiMessageId = `msg_${Date.now() + 1}`;
    setMessages((prev) => [
      ...prev,
      {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      },
    ]);

    try {
      // 使用 SSE 流式响应
      await api.stream(
        '/chat/send',
        { message: input.trim(), stream: true },
        (chunk) => {
          if (chunk.type === 'content' && chunk.content) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: msg.content + chunk.content }
                  : msg
              )
            );
          }
        }
      );
    } catch (error) {
      console.error('发送消息失败:', error);
      const errorMessage = `[连接错误] 无法连接到数字分身。请检查后端服务是否启动，或 API 密钥是否有效。`;
      
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? { ...msg, content: errorMessage }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // 快捷提示
  const quickPrompts = [
    '今天的目标是什么？',
    '帮我回顾一下本周进展',
    '我感到有点迷茫...',
    '如何提升我的专注力？',
  ];

  return (
    <div className="chat-page">
      {/* 页面标题 */}
      <header className="chat-header">
        <div className="chat-header-content">
          <div className="chat-header-info">
            <h1 className="page-title" style={{ marginBottom: '4px' }}>
              与 The Architect 对话
            </h1>
            <p className="page-subtitle">
              你的数字分身，帮助你保持终局聚焦
            </p>
          </div>
          <button className="btn btn-ghost chat-new-btn">
            <RefreshCw size={18} />
            <span className="btn-text">新对话</span>
          </button>
        </div>
      </header>

      {/* 消息列表 */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          // 空状态
          <div className="chat-empty-state">
            <div className="chat-empty-icon">
              <Sparkles size={40} className="text-white" />
            </div>
            <h2 className="chat-empty-title">
              开始对话
            </h2>
            <p className="chat-empty-desc">
              与你的数字分身交流，分享你的想法、目标和困惑。
              我会帮助你保持对终局愿景的聚焦。
            </p>
            
            {/* 快捷提示 */}
            <div className="chat-quick-prompts">
              {quickPrompts.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setInput(prompt);
                    inputRef.current?.focus();
                  }}
                  className="chat-quick-prompt"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          // 消息列表
          <div className="chat-messages-inner" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            {messages.map((message) => (
              <div
                key={message.id}
                className={clsx(
                  'chat-message animate-fade-in-up',
                  message.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'
                )}
              >
                {message.role === 'assistant' && (
                  <div className="chat-avatar chat-avatar-ai">
                    <Sparkles size={20} className="text-white" />
                  </div>
                )}
                
                <div className={clsx('message-bubble', message.role === 'user' ? 'message-bubble-user' : 'message-bubble-assistant')}>
                  <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {message.content}
                    {message.role === 'assistant' && isLoading && message.id === messages[messages.length - 1]?.id && (
                      <span className="chat-typing-cursor" />
                    )}
                  </p>
                </div>

                {message.role === 'user' && (
                  <div className="chat-avatar chat-avatar-user">
                    <span>{user?.name?.charAt(0).toUpperCase() || 'U'}</span>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className="chat-input-inner">
          <div className="chat-input-wrapper">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的想法..."
              rows={1}
              className="chat-textarea"
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = `${Math.min(target.scrollHeight, 128)}px`;
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className={clsx('chat-send-btn', input.trim() && !isLoading && 'chat-send-btn-active')}
            >
              {isLoading ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
          <p className="chat-input-hint">
            按 Enter 发送，Shift + Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}

