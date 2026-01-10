/**
 * Endgame OS v2 - Chat Page
 * Strictly following M3 Conversational UI guidelines
 */
import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Sparkles, Plus, Image as ImageIcon, Mic, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import GlassCard from '../components/layout/GlassCard';
import { useChatStore } from '../stores/useChatStore';
import { useAuthStore } from '../stores/useAuthStore';
import { useH3Store } from '../stores/useH3Store';
import api from '../lib/api';
import clsx from 'clsx';

export default function ChatPage() {
  const { messages, addMessage, updateLastMessage, isStreaming, setStreaming, setError, clearMessages } = useChatStore();
  const { scores } = useH3Store();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整输入框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleClearHistory = () => {
    if (window.confirm('确定要清除所有聊天记录吗？此操作不可撤销。')) {
      clearMessages();
    }
  };

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    
    const query = input.trim();
    setInput('');
    
    // 1. 添加用户消息
    const userMessage = {
      role: 'user' as const,
      content: query,
      timestamp: Date.now(),
    };
    addMessage(userMessage);
    setStreaming(true);
    setError(null);

    // 2. 先添加一个空的助手消息，准备接收流
    addMessage({
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    });

    try {
      // 3. 调用流式 API
      await api.stream(
        '/chat/send',
        {
          message: query,
          context: {
            h3_state: scores
          },
          stream: true
        },
        (chunk) => {
          if (chunk.type === 'content' && chunk.content) {
            updateLastMessage(chunk.content);
          } else if (chunk.type === 'error') {
            setError(chunk.content || '生成出错');
          }
        }
      );
    } catch (err) {
      console.error('发送消息失败:', err);
      const errorMessage = err instanceof Error ? err.message : '发送失败，请检查网络连接';
      setError(errorMessage);
      updateLastMessage(`\n\n抱歉，发生了错误：${errorMessage}`);
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-var(--md-sys-spacing-8))] max-w-4xl mx-auto w-full relative">
      
      {/* 1. CHAT HEADER - 简约 M3 风格 */}
      <header className="flex items-center justify-between py-4 px-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[var(--md-sys-color-primary-container)] flex items-center justify-center text-[var(--md-sys-color-on-primary-container)] shadow-sm">
            <Bot size={20} />
          </div>
          <div>
            <h2 className="text-[var(--md-sys-typescale-title-large-size)] font-bold">Endgame AI</h2>
            <div className="flex items-center gap-1.5">
              <span className={clsx(
                "w-2 h-2 rounded-full animate-pulse",
                "bg-green-500" // 简化状态显示，默认为在线
              )} />
              <span className="text-[var(--md-sys-typescale-label-large-size)] opacity-60">在线 · 深度思考模式</span>
            </div>
          </div>
        </div>
        <button 
          onClick={handleClearHistory}
          className="p-2 rounded-full hover:bg-[var(--md-sys-color-error-container)] hover:text-[var(--md-sys-color-error)] transition-all group relative"
          title="清除所有历史记录"
        >
          <Trash2 size={20} className="text-[var(--md-sys-color-on-surface-variant)] group-hover:text-[var(--md-sys-color-error)]" />
        </button>
      </header>

      {/* 2. MESSAGES LIST */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-[var(--md-sys-spacing-3)] py-[var(--md-sys-spacing-4)] px-2 scrollbar-hide"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-6 opacity-60">
            <div className="w-20 h-20 rounded-[var(--md-sys-shape-corner-extra-large)] bg-[var(--md-sys-color-surface-container)] flex items-center justify-center">
              <MessageSquare size={40} className="text-[var(--md-sys-color-primary)]" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl font-bold">开始一次深度对话</h3>
              <p className="max-w-xs mx-auto">探讨你的终局愿景，或者只是进行一次 H3 能量校准</p>
            </div>
            <div className="grid grid-cols-2 gap-3 w-full max-w-md">
              {['今日心智校准', '分析我的志业目标', '提升身体能量建议', '寻找精神共鸣'].map(tag => (
                <button 
                  key={tag} 
                  onClick={() => setInput(tag)}
                  className="p-3 rounded-xl border border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container)] transition-colors text-sm"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div 
              key={i}
              className={clsx(
                "flex w-full animate-fade-in",
                msg.role === 'user' ? "justify-end" : "justify-start"
              )}
            >
              <div className={clsx(
                "flex gap-3 max-w-[85%]",
                msg.role === 'user' && "flex-row-reverse"
              )}>
                <div className={clsx(
                  "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center mt-1",
                  msg.role === 'user' ? "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)]" : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)]"
                )}>
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                
                <div className={clsx(
                  "px-4 py-3 rounded-[var(--md-sys-shape-corner-large)] text-[var(--md-sys-typescale-body-large-size)] leading-relaxed",
                  msg.role === 'user' 
                    ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] rounded-tr-none" 
                    : "bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] rounded-tl-none"
                )}>
                  {msg.role === 'user' ? (
                     msg.content
                   ) : (
                     <div className="prose prose-sm prose-invert max-w-none">
                       <ReactMarkdown>
                         {msg.content}
                       </ReactMarkdown>
                     </div>
                   )}
                </div>
              </div>
            </div>
          ))
        )}
        {isStreaming && (
          <div className="flex justify-start animate-pulse">
            <div className="bg-[var(--md-sys-color-surface-container-high)] px-6 py-3 rounded-full flex gap-2">
              <span className="w-2 h-2 bg-[var(--md-sys-color-primary)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-[var(--md-sys-color-primary)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-[var(--md-sys-color-primary)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
      </div>

      {/* 3. INPUT AREA - M3 FAB Style */}
      <div className="pt-4 pb-6 px-2">
        <GlassCard 
          variant="elevated" 
          padding="none" 
          className="flex items-center gap-2 p-1.5 pr-3 shadow-lg ring-1 ring-[var(--md-sys-color-outline-variant)]"
        >
          <button className="p-3 rounded-full hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] transition-colors">
            <Plus size={22} />
          </button>
          <textarea 
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="与 Endgame AI 对话..."
            className="flex-1 bg-transparent border-none outline-none py-3 px-2 text-[var(--md-sys-typescale-body-large-size)] placeholder:opacity-40 resize-none min-h-[52px] max-h-[200px] leading-relaxed"
            disabled={isStreaming}
            rows={1}
          />
          <div className="flex items-center gap-1">
             <button className="p-2 rounded-full hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] transition-colors">
               <ImageIcon size={20} />
             </button>
             <button className="p-2 rounded-full hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] transition-colors">
               <Mic size={20} />
             </button>
          </div>
          <button 
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className={clsx(
              "p-3 rounded-full transition-all active:scale-90",
              input.trim() && !isStreaming
                ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-md" 
                : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] opacity-40"
            )}
          >
            <Send size={20} />
          </button>
        </GlassCard>
        <p className="text-center text-[var(--md-sys-typescale-label-large-size)] opacity-40 mt-3">
          AI 可能生成不准确的信息，请在重要决策前核实
        </p>
      </div>
    </div>
  );
}

// 补全缺失的 Icon
function MessageSquare({ size, className }: { size: number, className?: string }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
