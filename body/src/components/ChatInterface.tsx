/**
 * ChatInterface 组件
 * 聊天界面组件，支持文件上传和记忆管理
 */
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, RefreshCw, Upload, Database, Trash2, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { useChatStore, type Message } from '../stores/useChatStore';
import { useH3Store } from '../stores/useH3Store';

interface MemoryStats {
  total_documents: number;
  collection_name: string;
  persist_directory: string;
}

export default function ChatInterface() {
  // Zustand Stores
  const { messages, isStreaming, error, addMessage, setStreaming, setError } = useChatStore();
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
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  useEffect(() => {
    fetchMemoryStats();
  }, []);

  const fetchMemoryStats = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8002/api/memory/stats');
      if (response.ok) {
        const stats = await response.json();
        setMemoryStats(stats);
      }
    } catch (err) {
      console.error('获取记忆统计失败:', err);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = {
      role: 'user' as const,
      content: input.trim(),
      timestamp: Date.now(),
    };

    addMessage(userMessage);
    setInput('');
    setStreaming(true);
    setError(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000);

      const response = await fetch('http://127.0.0.1:8002/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage.content,
          context: '',
          h3_state: scores, // 注入 H3 状态
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      addMessage({
        role: 'assistant',
        content: data.response,
        timestamp: Date.now(),
      });
    } catch (err) {
      console.error('Error sending message:', err);
      let errorMessage = '连接失败';
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMessage = '请求超时，请稍后重试';
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
      setIsConnected(false);
      
      addMessage({
        role: 'assistant',
        content: `抱歉，发生了错误：${errorMessage}`,
        timestamp: Date.now(),
      });
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

  const handleRetry = () => {
    setError(null);
    setIsConnected(true);
    addMessage({
      role: 'assistant',
      content: '正在重新连接...',
      timestamp: Date.now(),
    });
    
    setTimeout(async () => {
      try {
        const response = await fetch('http://127.0.0.1:8002/health');
        if (response.ok) {
          setIsConnected(true);
          // 这里不再删除最后一条消息，而是直接提示成功
          addMessage({
            role: 'assistant',
            content: '连接成功！',
            timestamp: Date.now(),
          });
        } else {
          throw new Error('后端服务不可用');
        }
      } catch (err) {
        setError('无法连接到后端服务');
      }
    }, 500);
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
    const filePaths: string[] = [];

    try {
      for (const file of uploadedFiles) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://127.0.0.1:8002/api/upload', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          filePaths.push(result.file_path);
        }
      }

      if (filePaths.length > 0) {
        const trainResponse = await fetch('http://127.0.0.1:8002/api/train', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ file_paths: filePaths }),
        });

        if (trainResponse.ok) {
          const trainResult = await trainResponse.json();
          addMessage({
            role: 'assistant',
            content: `记忆训练完成！成功处理 ${trainResult.success} 个文件，失败 ${trainResult.failed} 个。`,
            timestamp: Date.now(),
          });
          await fetchMemoryStats();
        }
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

  const handleClearMemory = async () => {
    if (!confirm('确定要清空所有记忆吗？此操作不可恢复。')) return;

    try {
      const response = await fetch('http://127.0.0.1:8002/api/memory/clear', {
        method: 'DELETE',
      });

      if (response.ok) {
        addMessage({
          role: 'assistant',
          content: '记忆已清空',
          timestamp: Date.now(),
        });
        await fetchMemoryStats();
      }
    } catch (err) {
      console.error('清空记忆失败:', err);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-100 flex items-center justify-center p-6">
      <div className="w-full max-w-6xl bg-white/90 backdrop-blur-2xl rounded-3xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <div className={clsx(
                'w-3 h-3 rounded-full',
                isConnected ? 'bg-green-500' : 'bg-red-500'
              )} />
              <span className="text-sm text-gray-600">
                {isConnected ? '大脑在线' : '大脑离线'}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-800">
              Endgame OS
            </h1>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowMemoryPanel(!showMemoryPanel)}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700"
            >
              <Database size={18} />
              <span className="text-sm">记忆</span>
              {memoryStats && (
                <span className="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-600 rounded-full text-xs">
                  {memoryStats.total_documents}
                </span>
              )}
            </button>
            {error && (
              <button
                onClick={handleRetry}
                className="flex items-center space-x-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                <RefreshCw size={16} />
                <span>重试连接</span>
              </button>
            )}
          </div>
        </div>

        {showMemoryPanel && (
          <div className="border-b border-gray-200 p-6 bg-gray-50">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800">记忆管理</h3>
                <button
                  onClick={handleClearMemory}
                  className="flex items-center space-x-2 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-600 rounded-lg transition-colors text-sm"
                >
                  <Trash2 size={14} />
                  <span>清空记忆</span>
                </button>
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={clsx(
                  'border-2 border-dashed rounded-xl p-8 text-center transition-all',
                  isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-gray-300 hover:border-gray-400'
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt,.json"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Upload className="mx-auto mb-4 text-gray-500" size={48} />
                <p className="text-gray-600 mb-2">拖拽文件到此处，或点击上传</p>
                <p className="text-sm text-gray-500 mb-4">支持 PDF、Markdown、TXT、JSON 格式</p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  选择文件
                </button>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">已选择 {uploadedFiles.length} 个文件</span>
                    <button
                      onClick={handleUploadFiles}
                      disabled={isTraining}
                      className={clsx(
                        'px-4 py-2 rounded-lg transition-colors',
                        isTraining
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-green-600 hover:bg-green-700 text-white'
                      )}
                    >
                      {isTraining ? (
                        <>
                          <Loader2 size={16} className="animate-spin inline mr-2" />
                          训练中...
                        </>
                      ) : (
                        '开始训练'
                      )}
                    </button>
                  </div>
                  <div className="space-y-1">
                    {uploadedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between px-3 py-2 bg-gray-100 rounded-lg"
                      >
                        <div className="flex items-center space-x-2">
                          <FileText size={16} className="text-gray-500" />
                          <span className="text-sm text-gray-700">{file.name}</span>
                          <span className="text-xs text-gray-500">({(file.size / 1024).toFixed(1)} KB)</span>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-gray-500 hover:text-red-500 transition-colors"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-gray-500">
              <div className="text-center space-y-4">
                <div className="flex justify-center mb-4">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
                <p className="text-lg">开始与你的数字分身对话...</p>
                <p className="text-sm text-gray-400">我是你的终局架构师，准备好聆听你的想法</p>
                {memoryStats && memoryStats.total_documents > 0 && (
                  <p className="text-sm text-blue-500 mt-4">
                    我已经记住了 {memoryStats.total_documents} 个知识点
                  </p>
                )}
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={clsx(
                'flex mb-4',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div className="flex items-end space-x-2 mb-1">
                {message.role === 'assistant' && (
                  <span className="text-xs text-gray-400">
                    {new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>
              <div
                className={clsx(
                  'max-w-[80%] rounded-2xl px-5 py-4 shadow-lg',
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-800 border border-gray-200'
                )}
              >
                {message.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-white">{message.content}</p>
                )}
              </div>
            </div>
          ))}

          {isStreaming && (
            <div className="flex justify-start mb-4">
              <div className="bg-white text-gray-800 rounded-2xl px-5 py-4 border border-gray-200">
                <div className="flex items-center space-x-3">
                  <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  <span className="text-gray-500">正在思考...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex items-center space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入你的问题..."
              className="flex-1 bg-white text-gray-900 placeholder-gray-400 rounded-xl px-5 py-4 outline-none focus:ring-2 focus:ring-blue-500/50 transition-all border border-gray-300"
              disabled={isStreaming || !isConnected}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming || !isConnected}
              className={clsx(
                'p-4 rounded-xl transition-colors',
                input.trim() && !isStreaming && isConnected
                  ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              )}
            >
              {isStreaming ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}