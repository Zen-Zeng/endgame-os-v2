/**
 * ChatInterface 组件
 * 聊天界面组件，支持文件上传和记忆管理
 */
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, RefreshCw, Database, Trash2, FileText, Plus, Mic, Bot, Sparkles } from 'lucide-react';
import { clsx } from 'clsx';
import { useChatStore } from '../stores/useChatStore';
import { useH3Store } from '../stores/useH3Store';
import api from '../lib/api';
import GlassCard from './layout/GlassCard';
import Button from './ui/Button';

interface MemoryStats {
  total_documents: number;
  collection_name: string;
  persist_directory: string;
}

export default function ChatInterface() {
  // Zustand Stores
  const { messages, isStreaming, error, addMessage, updateLastMessage, setStreaming, setError } = useChatStore();
  const { scores } = useH3Store();

  // Local UI State
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(true);
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isTraining, setIsTraining] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  useEffect(() => {
    fetchMemoryStats();
  }, []);

  const fetchMemoryStats = async () => {
    try {
      const stats = await api.get<MemoryStats>('/memory/stats');
      setMemoryStats(stats);
    } catch (err) {
      console.error('获取记忆统计失败:', err);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const query = input.trim();
    const userMessage = {
      role: 'user' as const,
      content: query,
      timestamp: Date.now(),
    };

    addMessage(userMessage);
    setInput('');
    setStreaming(true);
    setError(null);

    // 先添加一个空的助手消息，准备接收流
    addMessage({
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    });

    try {
      await api.stream(
        '/chat/send',
        {
          message: query,
          context: {
            h3_state: scores
          },
          stream: true
        },
        (chunk: any) => {
          if (chunk.type === 'content' && chunk.content) {
            updateLastMessage(chunk.content);
          } else if (chunk.type === 'meta' && chunk.metadata) {
            updateLastMessage(null, chunk.metadata);
          } else if (chunk.type === 'error') {
            setError(chunk.content || '生成出错');
          }
        }
      );
    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = err instanceof Error ? err.message : '发送失败，请检查网络连接';
      
      setError(errorMessage);
      setIsConnected(false);
      
      updateLastMessage(`\n\n抱歉，发生了错误：${errorMessage}`);
    } finally {
      setStreaming(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleRetry = async () => {
    setError(null);
    setIsConnected(true);
    
    try {
      const response: any = await api.get('/health');
      if (response.status === 'ok') {
        setIsConnected(true);
        addMessage({
          role: 'assistant',
          content: '系统连接已恢复。',
          timestamp: Date.now(),
        });
      }
    } catch (err) {
      setError('无法连接到大脑服务');
      setIsConnected(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setUploadedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files) {
      const newFiles = Array.from(e.dataTransfer.files);
      setUploadedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleUploadFiles = async () => {
    if (uploadedFiles.length === 0) return;

    setIsTraining(true);
    const filenames: string[] = [];

    try {
      for (const file of uploadedFiles) {
        const formData = new FormData();
        formData.append('file', file);

        const result: any = await api.post('/archives/upload', formData);
        if (result.filename) {
          filenames.push(result.filename);
        }
      }

      if (filenames.length > 0) {
        addMessage({
          role: 'assistant',
          content: `文件上传成功。如果是聊天记录 JSON 文件，已自动进行拆分。你可以在“记忆图谱”页面手动选择并开始训练。`,
          timestamp: Date.now(),
        });
        await fetchMemoryStats();
      }
    } catch (err) {
      console.error('上传文件失败:', err);
      addMessage({
        role: 'assistant',
        content: `上传失败：${err instanceof Error ? err.message : '未知错误'}`,
        timestamp: Date.now(),
      });
    } finally {
      setIsTraining(false);
      setUploadedFiles([]);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* 顶部状态栏 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-black/20">
        <div className="flex items-center space-x-2">
          <Bot className="w-5 h-5 text-primary-400" />
          <h2 className="text-sm font-medium text-white/90">数字分身 - Architect</h2>
          {!isConnected && (
            <div className="flex items-center space-x-1 px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px]">
              <span className="w-1 h-1 rounded-full bg-red-500 animate-pulse" />
              <span>连接断开</span>
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <Button 
            variant="text" 
            onClick={() => setShowMemoryPanel(!showMemoryPanel)}
            className={clsx("p-1.5 h-10 w-10", showMemoryPanel && "bg-white/10")}
            icon={<Database className="w-4 h-4" />}
          >
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* 聊天消息区域 */}
        <div className="flex-1 flex flex-col min-w-0 relative">
          <div 
            className={clsx(
              "flex-1 overflow-y-auto px-4 py-6 space-y-6 scrollbar-hide",
              isDragging && "bg-primary-500/5 ring-2 ring-primary-500/30 ring-inset"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50 px-8">
                <div className="p-4 rounded-full bg-white/5 border border-white/10">
                  <Bot className="w-8 h-8 text-primary-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white">开始对话</h3>
                  <p className="text-sm text-white/60 max-w-xs mt-1">
                    我是你的数字分身 Architect。我们可以讨论你的终局愿景、项目进度或任何你想聊的话题。
                  </p>
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={clsx(
                    "flex w-full",
                    msg.role === 'user' ? "justify-end" : "justify-start"
                  )}
                >
                  <div className={clsx(
                    "max-w-[85%] flex space-x-3",
                    msg.role === 'user' && "flex-row-reverse space-x-reverse"
                  )}>
                    <div className={clsx(
                      "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border",
                      msg.role === 'user' 
                        ? "bg-primary-500/20 border-primary-500/30 text-primary-400" 
                        : "bg-white/5 border-white/10 text-white/60"
                    )}>
                      {msg.role === 'user' ? <Mic className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className={clsx(
                      "px-4 py-3 rounded-2xl text-sm leading-relaxed",
                      msg.role === 'user' 
                        ? "bg-primary-600/20 border border-primary-500/30 text-white/90 rounded-tr-none" 
                        : "bg-white/5 border border-white/10 text-white/80 rounded-tl-none"
                    )}>
                      {msg.role === 'assistant' && msg.metadata?.strategies && (
                        <div className="mb-3 flex flex-wrap gap-2">
                          {(msg.metadata.strategies as string[]).map((strategy, i) => (
                            <span key={i} className="px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-300 text-[10px] border border-primary-500/30 flex items-center gap-1 w-fit">
                              <Sparkles className="w-3 h-3" />
                              {strategy}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {isStreaming && (
              <div className="flex justify-start">
                <div className="flex space-x-3">
                  <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/60">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="bg-white/5 border border-white/10 px-4 py-3 rounded-2xl rounded-tl-none">
                    <div className="flex space-x-1.5 items-center h-5">
                      <span className="w-1.5 h-1.5 bg-primary-400/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 bg-primary-400/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 bg-primary-400/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {error && !isStreaming && (
              <div className="flex flex-col items-center justify-center p-4 space-y-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                <p className="text-xs text-red-400">{error}</p>
                <Button 
                  variant="outlined" 
                  onClick={handleRetry} 
                  className="text-xs h-8 px-3"
                  icon={<RefreshCw className="w-3 h-3" />}
                >
                  重试连接
                </Button>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="p-4 bg-gradient-to-t from-black/40 to-transparent">
            {uploadedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {uploadedFiles.map((file, i) => (
                  <div key={i} className="flex items-center space-x-2 px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-[10px] text-white/60">
                    <FileText className="w-3 h-3" />
                    <span className="truncate max-w-[100px]">{file.name}</span>
                    <button onClick={() => setUploadedFiles(prev => prev.filter((_, idx) => idx !== i))}>
                      <Trash2 className="w-3 h-3 hover:text-red-400" />
                    </button>
                  </div>
                ))}
                <Button 
                  onClick={handleUploadFiles} 
                  disabled={isTraining}
                  className="text-[10px] h-8 px-2"
                  variant="tonal"
                  icon={isTraining ? <Loader2 className="w-3 h-3 animate-spin" /> : <Database className="w-3 h-3" />}
                >
                  加入记忆
                </Button>
              </div>
            )}

            <GlassCard className="flex items-end space-x-2 p-2 focus-within:ring-1 ring-primary-500/30 transition-all">
              <button 
                className="p-2 text-white/40 hover:text-white/70 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Plus className="w-5 h-5" />
              </button>
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                multiple 
                onChange={handleFileSelect}
              />
              
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="与 Architect 交流..."
                rows={1}
                className="flex-1 bg-transparent border-none focus:ring-0 text-sm text-white/90 placeholder:text-white/30 py-2 resize-none max-h-32"
                style={{ height: 'auto' }}
              />
              
              <Button 
                onClick={handleSend} 
                disabled={!input.trim() || isStreaming}
                className={clsx(
                  "p-2 rounded-xl transition-all",
                  input.trim() ? "bg-primary-600 hover:bg-primary-500 shadow-lg shadow-primary-900/20" : "bg-white/5"
                )}
              >
                {isStreaming ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </Button>
            </GlassCard>
          </div>
        </div>

        {/* 记忆面板 (右侧侧边栏) */}
        {showMemoryPanel && (
          <div className="w-64 border-l border-white/10 bg-black/40 p-4 flex flex-col space-y-4 overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider">记忆统计</h3>
              <div className="flex items-center space-x-1">
                <Button 
                  variant="text" 
                  onClick={fetchMemoryStats}
                  className="h-8 w-8 p-0"
                  icon={<RefreshCw className={clsx("w-4 h-4", isTraining && "animate-spin")} />}
                />
                <Button 
                  variant="text" 
                  onClick={() => setShowMemoryPanel(false)}
                  className="h-8 px-2"
                >
                  关闭
                </Button>
              </div>
            </div>
            
            {memoryStats ? (
              <div className="space-y-3">
                <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                  <p className="text-[10px] text-white/40">已存文档</p>
                  <p className="text-xl font-semibold text-primary-400">{memoryStats.total_documents}</p>
                </div>
                <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                  <p className="text-[10px] text-white/40">向量库状态</p>
                  <p className="text-xs text-white/80 mt-1">已激活 (ChromaDB)</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="w-5 h-5 animate-spin text-white/20" />
              </div>
            )}
            
            <div className="pt-4 border-t border-white/5">
              <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">知识库操作</h3>
              <div className="space-y-2">
                <Button variant="text" className="w-full justify-start text-xs text-white/60 hover:text-white h-8 px-2" icon={<FileText className="w-3.5 h-3.5" />}>
                  查看所有文档
                </Button>
                <Button variant="text" className="w-full justify-start text-xs text-white/60 hover:text-white h-8 px-2" icon={<RefreshCw className="w-3.5 h-3.5" />}>
                  重新构建索引
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}