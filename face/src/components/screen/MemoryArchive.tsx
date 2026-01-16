import { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Trash2, 
  CheckSquare, 
  Square, 
  Scissors, 
  Loader2, 
  FileText, 
  Image, 
  File,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  RefreshCw,
  Zap,
  Upload,
  BrainCircuit,
  Share2,
  Target,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink
} from 'lucide-react';
import Button from '../ui/Button';
import api from '../../lib/api';
import clsx from 'clsx';

interface ArchiveFile {
  id: string;
  original_name: string;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
  tags: string[];
  is_processed: boolean;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  message?: string;
}

interface TaskStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  error?: string;
}

interface LineageNode {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'confirmed';
}

const fileTypeIcons: Record<string, typeof File> = {
  markdown: FileText,
  text: FileText,
  image: Image,
  csv: File,
  json: FileText,
  default: File,
};

const pipelineSteps = [
  { id: 'parse', label: '解析', icon: FileText },
  { id: 'structure', label: '提取', icon: BrainCircuit },
  { id: 'index', label: '索引', icon: Share2 },
  { id: 'calibrate', label: '校准', icon: Target },
];

interface MemoryArchiveProps {
  onRefreshGraph?: () => void;
  className?: string;
}

export default function MemoryArchive({ onRefreshGraph, className }: MemoryArchiveProps) {
  const [availableFiles, setAvailableFiles] = useState<ArchiveFile[]>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTasks, setActiveTasks] = useState<Record<string, TaskStatus>>({});
  const [expandedLineage, setExpandedLineage] = useState<Record<string, LineageNode[]>>({});
  const [isLoadingLineage, setIsLoadingLineage] = useState<Record<string, boolean>>({});
  const pageSize = 10;
  
  const pollingRef = useRef<any>(null);

  const fetchFiles = async () => {
    try {
      setIsLoadingFiles(true);
      const files: any = await api.get('/archives/files?limit=1000');
      setAvailableFiles(files);
    } catch (error) {
      console.error('获取文件列表失败:', error);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  useEffect(() => {
    fetchFiles();
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // 轮询正在进行的任务状态
  useEffect(() => {
    const activeTaskIds = Object.keys(activeTasks).filter(id => 
      activeTasks[id].status === 'pending' || activeTasks[id].status === 'processing'
    );

    if (activeTaskIds.length > 0) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(async () => {
          const newActiveTasks = { ...activeTasks };
          let changed = false;

          for (const taskId of activeTaskIds) {
            try {
              const status = await api.get<TaskStatus>(`/memory/tasks/${taskId}`);
              newActiveTasks[taskId] = status;
              changed = true;
              
              if (status.status === 'completed' || status.status === 'failed') {
                // 如果完成，刷新文件列表以更新 is_processed 状态
                fetchFiles();
              }
            } catch (e) {
              console.error(`Poll task ${taskId} failed`, e);
            }
          }

          if (changed) setActiveTasks(newActiveTasks);
        }, 2000);
      }
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
  }, [activeTasks]);

  const filteredFiles = availableFiles.filter(f => 
    f.original_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const totalPages = Math.ceil(filteredFiles.length / pageSize);
  const paginatedFiles = filteredFiles.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    try {
      setIsProcessing(true);
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);
        const response: any = await api.post('/archives/upload', formData);
        
        // 上传后自动触发训练
        const trainRes: any = await api.post('/memory/train', { filenames: [response.filename] });
        if (trainRes.task_id) {
          setActiveTasks(prev => ({
            ...prev,
            [trainRes.task_id]: { id: trainRes.task_id, status: 'pending', progress: 0 }
          }));
          // 将任务 ID 与文件名关联（简化处理，实际可能需要更复杂的映射）
          // 这里我们只是启动了轮询
        }
      }
      fetchFiles();
    } catch (error: any) {
      console.error('上传失败:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTrainFile = async (file: ArchiveFile) => {
    try {
      setIsProcessing(true);
      const res: any = await api.post('/memory/train', { filenames: [file.filename] });
      if (res.task_id) {
        setActiveTasks(prev => ({
          ...prev,
          [res.task_id]: { id: res.task_id, status: 'pending', progress: 0 }
        }));
      }
    } catch (error) {
      console.error('训练触发失败:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleLineage = async (filename: string) => {
    if (expandedLineage[filename]) {
      const newExpanded = { ...expandedLineage };
      delete newExpanded[filename];
      setExpandedLineage(newExpanded);
      return;
    }

    try {
      setIsLoadingLineage(prev => ({ ...prev, [filename]: true }));
      const res: any = await api.get(`/memory/lineage/${filename}`);
      setExpandedLineage(prev => ({ ...prev, [filename]: res.nodes }));
    } catch (e) {
      console.error('获取贡献链失败', e);
    } finally {
      setIsLoadingLineage(prev => ({ ...prev, [filename]: false }));
    }
  };

  const getCurrentStepIndex = (message: string) => {
    if (!message) return -1;
    if (message.includes('解析')) return 0;
    if (message.includes('DeepSeek') || message.includes('结构化')) return 1;
    if (message.includes('向量化')) return 2;
    if (message.includes('图谱') || message.includes('写入')) return 3;
    return 0;
  };

  const toggleFileSelection = (fileId: string) => {
    setSelectedFileIds(prev => 
      prev.includes(fileId) ? prev.filter(id => id !== fileId) : [...prev, fileId]
    );
  };

  const handleBatchDelete = async () => {
    if (selectedFileIds.length === 0) return;
    if (!window.confirm(`确定要删除选中的 ${selectedFileIds.length} 个素材吗？`)) return;

    try {
      setIsProcessing(true);
      await Promise.all(selectedFileIds.map(id => api.delete(`/archives/files/${id}`)));
      setSelectedFileIds([]);
      fetchFiles();
    } catch (error: any) {
      console.error('批量删除失败:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSplitFile = async (fileId: string) => {
    try {
      setIsProcessing(true);
      await api.post(`/archives/split/${fileId}`);
      fetchFiles();
    } catch (error: any) {
      console.error('拆分失败:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '未知时间';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (isNaN(date.getTime())) return dateStr;
    const options: Intl.DateTimeFormatOptions = { 
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    };
    if (diff < 24 * 3600 * 1000 && now.getDate() === date.getDate()) {
      return `今天 ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    return date.toLocaleString('zh-CN', options);
  };

  return (
    <div className={clsx("flex flex-col bg-[var(--md-sys-color-surface-container-low)] rounded-[40px] border border-[var(--md-sys-color-outline-variant)] shadow-sm overflow-hidden", className)}>
      {/* 档案库头部：注入区 */}
      <div className="p-6 border-b border-[var(--md-sys-color-outline-variant)]">
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black flex items-center gap-2 uppercase tracking-tight">
              <FileText size={24} className="text-[var(--md-sys-color-primary)]" />
              战略情报工作台 / Intelligence Hub
            </h3>
            <div className="flex items-center gap-2">
              {selectedFileIds.length > 0 && (
                <Button
                  variant="tonal"
                  className="h-10 px-4 text-red-500 hover:bg-red-50 rounded-xl"
                  icon={<Trash2 size={16} />}
                  onClick={handleBatchDelete}
                  disabled={isProcessing}
                >
                  删除 ({selectedFileIds.length})
                </Button>
              )}
              <Button
                variant="text"
                className="h-10 w-10 p-0 rounded-xl"
                icon={<RefreshCw size={20} className={isLoadingFiles ? "animate-spin" : ""} />}
                onClick={fetchFiles}
                disabled={isLoadingFiles}
              />
            </div>
          </div>

          {/* 注入记忆入口 */}
          <div 
            className={clsx(
              "relative group p-6 rounded-3xl border-2 border-dashed transition-all duration-300 flex flex-col items-center justify-center gap-4 text-center cursor-pointer",
              isProcessing ? "border-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-primary)]/5" : "border-[var(--md-sys-color-outline-variant)] hover:border-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-surface-container-high)]"
            )}
            onClick={() => document.getElementById('archive-upload-input')?.click()}
          >
            <input
              id="archive-upload-input"
              type="file"
              className="hidden"
              onChange={handleFileUpload}
              multiple
            />
            
            <div className={clsx(
              "w-16 h-16 rounded-3xl flex items-center justify-center transition-all duration-500",
              isProcessing ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] rotate-180" : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] group-hover:scale-110 group-hover:rotate-12"
            )}>
              {isProcessing ? <Loader2 size={32} className="animate-spin" /> : <Upload size={32} />}
            </div>

            <div className="space-y-1">
              <h4 className="font-black text-sm uppercase tracking-widest">注入记忆 / Ingest Memory</h4>
              <p className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] font-bold opacity-60">支持拖拽文件或点击上传 (PDF, MD, JSON, TXT)</p>
            </div>

            <div className="absolute top-2 right-2">
              <div className="p-1.5 bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] rounded-lg shadow-sm">
                <Zap size={14} className="animate-pulse" />
              </div>
            </div>
          </div>

          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--md-sys-color-outline)]" size={18} />
            <input
              type="text"
              placeholder="搜索档案情报..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 h-12 bg-[var(--md-sys-color-surface)] rounded-2xl border border-[var(--md-sys-color-outline-variant)] focus:ring-2 focus:ring-[var(--md-sys-color-primary)] transition-all"
            />
          </div>
        </div>
      </div>

      {/* 列表区域：流水线卡片 */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4 min-h-[400px]">
        {isLoadingFiles ? (
          <div className="flex flex-col items-center justify-center h-full py-20 gap-4 opacity-50">
            <Loader2 className="animate-spin text-[var(--md-sys-color-primary)]" size={32} />
            <span className="text-sm font-black uppercase tracking-widest">同步情报中...</span>
          </div>
        ) : paginatedFiles.length > 0 ? (
          paginatedFiles.map(file => {
            const Icon = fileTypeIcons[file.file_type] || fileTypeIcons.default;
            const task = Object.values(activeTasks).find(t => 
              t.message?.includes(file.filename) || t.message?.includes(file.original_name)
            );
            const isTaskRunning = task?.status === 'pending' || task?.status === 'processing';
            const stepIdx = isTaskRunning ? getCurrentStepIndex(task?.message || '') : (file.is_processed ? 4 : -1);

            return (
              <div 
                key={file.id} 
                className={clsx(
                  "group relative bg-[var(--md-sys-color-surface)] rounded-3xl border border-[var(--md-sys-color-outline-variant)] hover:border-[var(--md-sys-color-primary)]/50 transition-all duration-300 overflow-hidden",
                  selectedFileIds.includes(file.id) && "ring-2 ring-[var(--md-sys-color-primary)]"
                )}
              >
                <div className="p-5 flex flex-col gap-4">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => toggleFileSelection(file.id)}
                      className="text-[var(--md-sys-color-primary)]"
                    >
                      {selectedFileIds.includes(file.id) ? <CheckSquare size={20} /> : <Square size={20} className="opacity-20 group-hover:opacity-100" />}
                    </button>

                    <div className="p-3 bg-[var(--md-sys-color-surface-variant)] rounded-2xl text-[var(--md-sys-color-on-surface-variant)]">
                      <Icon size={24} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-black text-sm truncate uppercase tracking-tight">{file.original_name}</span>
                        {file.is_processed ? (
                          <span className="px-1.5 py-0.5 rounded-md bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] text-[8px] font-black uppercase">已归一化</span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded-md bg-[var(--md-sys-color-surface-variant)] text-[var(--md-sys-color-on-surface-variant)] text-[8px] font-black uppercase">待处理</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1 opacity-60">
                        <span className="text-[10px] font-bold">{formatFileSize(file.file_size)}</span>
                        <span className="text-[10px] font-bold">•</span>
                        <span className="text-[10px] font-bold">{formatDate(file.created_at)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      {file.is_processed && (
                        <button 
                          onClick={() => toggleLineage(file.filename)}
                          className="p-2 hover:bg-[var(--md-sys-color-surface-variant)] rounded-xl text-[var(--md-sys-color-primary)] transition-colors"
                          title="查看贡献链"
                        >
                          {expandedLineage[file.filename] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                        </button>
                      )}
                      <button 
                        onClick={() => handleTrainFile(file)}
                        className={clsx(
                          "p-2 hover:bg-[var(--md-sys-color-surface-variant)] rounded-xl text-[var(--md-sys-color-tertiary)] transition-all",
                          isTaskRunning && "animate-pulse"
                        )}
                        title="大脑训练"
                        disabled={isTaskRunning}
                      >
                        <Zap size={20} className={isTaskRunning ? "fill-current" : ""} />
                      </button>
                      {file.file_type === 'json' && (
                        <button 
                          onClick={() => handleSplitFile(file.id)}
                          className="p-2 hover:bg-[var(--md-sys-color-surface-variant)] rounded-xl text-[var(--md-sys-color-primary)]"
                          title="拆分对话"
                        >
                          <Scissors size={18} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 四段式流水线进度条 */}
                  {(isTaskRunning || file.is_processed) && (
                    <div className="flex items-center gap-2 px-2">
                      {pipelineSteps.map((step, idx) => {
                        const isCompleted = idx < stepIdx || (file.is_processed && !isTaskRunning);
                        const isActive = idx === stepIdx;
                        return (
                          <div key={step.id} className="flex-1 flex flex-col gap-1.5">
                            <div className={clsx(
                              "h-1.5 rounded-full transition-all duration-500",
                              isActive ? "bg-[var(--md-sys-color-primary)] animate-pulse" : 
                              isCompleted ? "bg-[var(--md-sys-color-primary)]" : "bg-[var(--md-sys-color-surface-variant)]"
                            )} />
                            <div className="flex items-center justify-center gap-1 opacity-40">
                              <step.icon size={10} />
                              <span className="text-[8px] font-black uppercase">{step.label}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* 穿透式预览：贡献链条 */}
                  {expandedLineage[file.filename] && (
                    <div className="mt-2 p-4 bg-[var(--md-sys-color-surface-container-high)] rounded-2xl border border-dashed border-[var(--md-sys-color-outline-variant)] animate-in slide-in-from-top-2 duration-300">
                      <div className="flex items-center gap-2 mb-3">
                        <Target size={14} className="text-[var(--md-sys-color-tertiary)]" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-[var(--md-sys-color-on-surface-variant)]">战略贡献链 / Strategic Lineage</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {expandedLineage[file.filename].length > 0 ? (
                          expandedLineage[file.filename].map(node => (
                            <div 
                              key={node.id}
                              className={clsx(
                                "flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-[10px] font-bold transition-all hover:scale-105 cursor-pointer",
                                node.status === 'confirmed' 
                                  ? "bg-[var(--md-sys-color-primary-container)] border-[var(--md-sys-color-primary)]/20 text-[var(--md-sys-color-on-primary-container)]"
                                  : "bg-[var(--md-sys-color-surface-variant)] border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] italic"
                              )}
                            >
                              <span className="opacity-60">{node.type}:</span>
                              <span>{node.name}</span>
                              {node.status === 'confirmed' && <CheckCircle2 size={10} />}
                            </div>
                          ))
                        ) : (
                          <span className="text-[10px] font-bold opacity-40 italic">暂无提取到的战略实体</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex flex-col items-center justify-center h-full py-20 opacity-40">
            <FileText size={64} strokeWidth={1} className="text-[var(--md-sys-color-primary)]" />
            <p className="mt-4 text-sm font-black uppercase tracking-widest">暂无记忆档案 / Archive Empty</p>
          </div>
        )}
      </div>

      {/* 分页控制 */}
      {totalPages > 1 && (
        <div className="p-6 border-t border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-low)] flex items-center justify-between">
          <span className="text-xs font-black uppercase tracking-widest text-[var(--md-sys-color-outline)]">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="text"
              className="h-10 w-10 p-0 rounded-xl"
              icon={<ChevronLeft size={20} />}
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
            />
            <Button
              variant="text"
              className="h-10 w-10 p-0 rounded-xl"
              icon={<ChevronRight size={20} />}
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
            />
          </div>
        </div>
      )}
    </div>
  );
}
