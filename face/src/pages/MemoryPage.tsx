/**
 * 记忆图谱页面
 * 优化后的知识图谱可视化，整合档案库管理功能
 */
import { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  Upload, 
  BrainCircuit, 
  Trash2, 
  Target, 
  Library, 
  Activity, 
  MessageSquare, 
  Share2, 
  CheckSquare, 
  Square, 
  Scissors, 
  Loader2, 
  X,
  Grid,
  List,
  RefreshCw,
  MoreVertical,
  FileText,
  Image,
  File,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import StrategicPixiGraph from '../components/graph/StrategicPixiGraph';
import Button from '../components/ui/Button';
import api from '../lib/api';
import clsx from 'clsx';

interface GraphStats {
  nodes: number;
  links: number;
}

interface RecentUpdate {
  id: string;
  type: 'note' | 'link' | 'status';
  title: string;
  time: string;
}

interface GraphResponse {
  nodes: any[];
  links: any[];
}

interface TaskStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  error?: string;
}

interface ArchiveFile {
  id: string;
  original_name: string;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
  tags: string[];
  is_processed: boolean;
}

const fileTypeIcons: Record<string, typeof File> = {
  markdown: FileText,
  text: FileText,
  image: Image,
  csv: File,
  json: FileText,
  default: File,
};

// 节点类型配置 - 使用 M3 颜色令牌
const nodeTypes = [
  { key: 'Self', label: '我', color: '#6750A4', icon: BrainCircuit },
  { key: 'Vision', label: '愿景', color: '#B3261E', icon: Target },
  { key: 'Goal', label: '目标', color: '#E27396', icon: Target },
  { key: 'Project', label: '项目', color: '#7D5260', icon: Library },
  { key: 'Task', label: '任务', color: '#605D62', icon: Activity },
  { key: 'Person', label: '人物', color: '#3F5F90', icon: Share2 },
  { key: 'Concept', label: '概念', color: '#1D6F42', icon: Share2 },
];

export default function MemoryPage() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [searchQuery, setSearchQuery] = useState('');
  const [isConsolidating, setIsConsolidating] = useState(false);
  const [consolidationProgress, setConsolidationProgress] = useState(0);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [graphStats, setGraphStats] = useState<GraphStats>({ nodes: 0, links: 0 });
  const [recentUpdates, setRecentUpdates] = useState<RecentUpdate[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState<number | null>(null);
  const [trainingMessage, setTrainingMessage] = useState<string>('');
  
  // 文件管理状态
  const [availableFiles, setAvailableFiles] = useState<ArchiveFile[]>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // 过滤后的可用文件
  const filteredFiles = availableFiles.filter(f => 
    f.original_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 当搜索内容改变时，重置页码到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // 计算分页后的文件
  const totalPages = Math.ceil(filteredFiles.length / pageSize);
  const paginatedFiles = filteredFiles.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // 全选/取消全选 (改为仅针对当前页，或者保留全局全选？通常全选是针对所有过滤结果)
  const handleSelectAll = () => {
    if (selectedFileIds.length === filteredFiles.length) {
      setSelectedFileIds([]);
    } else {
      setSelectedFileIds(filteredFiles.map(f => f.id));
    }
  };

  // 获取图谱统计数据
  const fetchStats = async () => {
    try {
      setIsLoadingStats(true);
      const response = await api.get<GraphResponse>('/memory/graph');
      const nodes = Array.isArray(response.nodes) ? response.nodes : [];
      const links = Array.isArray(response.links) ? response.links : [];
      
      setGraphStats({
        nodes: nodes.length,
        links: links.length,
      });

      const overview: any = await api.get('/dashboard/overview');
      const activities = overview.activities || [];
      
      const updates: RecentUpdate[] = activities.map((act: any) => {
        let type: 'note' | 'link' | 'status' = 'note';
        if (act.type === 'calibration') type = 'status';
        if (act.entity_type === 'link') type = 'link';

        const date = new Date(act.created_at);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMin = Math.round(diffMs / 60000);
        let timeStr = '刚刚';
        if (diffMin > 0) {
          if (diffMin < 60) timeStr = `${diffMin} 分钟前`;
          else if (diffMin < 1440) timeStr = `${Math.round(diffMin / 60)} 小时前`;
          else timeStr = `${Math.round(diffMin / 1440)} 天前`;
        }

        return {
          id: act.id,
          type,
          title: act.title,
          time: timeStr
        };
      });

      setRecentUpdates(updates.slice(0, 5));
    } catch (error) {
      console.error('获取图谱统计失败:', error);
    } finally {
      setIsLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchFiles();
  }, []);

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

  const handleSplitFile = async (fileId: string) => {
    try {
      setIsProcessing(true);
      await api.post(`/archives/split/${fileId}`);
      fetchFiles();
    } catch (error: any) {
      console.error('拆分失败:', error);
      alert(`拆分失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleFileSelection = (fileId: string) => {
    setSelectedFileIds(prev => 
      prev.includes(fileId) ? prev.filter(id => id !== fileId) : [...prev, fileId]
    );
  };

  const handleTrainSelected = async () => {
    if (selectedFileIds.length === 0) return;
    
    try {
      setIsTraining(true);
      setTrainingProgress(0);
      setTrainingMessage('正在初始化批量训练...');
      
      const selectedFilenames = availableFiles
        .filter(f => selectedFileIds.includes(f.id))
        .map(f => f.filename);

      const trainResponse: any = await api.post('/memory/train', { 
        filenames: selectedFilenames 
      });
      
      const taskId = trainResponse.task_id;
      
      const timer = setInterval(async () => {
        try {
          const status = await api.get<TaskStatus>(`/memory/tasks/${taskId}`);
          setTrainingProgress(status.progress);
          setTrainingMessage(status.message || '训练中...');
          
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(timer);
            setIsTraining(false);
            setTrainingProgress(null);
            setTrainingMessage('');
            if (status.status === 'failed') {
              alert(`训练失败: ${status.error}`);
            } else {
              alert('批量训练完成！');
              fetchStats();
              setSelectedFileIds([]);
            }
          }
        } catch (error) {
          console.error('获取训练进度失败:', error);
          clearInterval(timer);
          setIsTraining(false);
          setTrainingProgress(null);
        }
      }, 1500);
    } catch (error: any) {
      console.error('开始批量训练失败:', error);
      alert(`批量训练失败: ${error.response?.data?.detail || error.message}`);
      setIsTraining(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setIsProcessing(true);
      setTrainingMessage('正在上传并处理...');
      const response: any = await api.post('/archives/upload', formData);
      
      if (file.name.toLowerCase().endsWith('.json')) {
        setTrainingMessage('正在解析对话主题...');
        await api.post(`/archives/split/${response.id}`);
      }
      
      fetchFiles();
      alert('素材上传成功！');
    } catch (error: any) {
      console.error('上传失败:', error);
      alert(`上传失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsProcessing(false);
      setTrainingMessage('');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedFileIds.length === 0) return;
    if (!window.confirm(`确定要删除选中的 ${selectedFileIds.length} 个素材吗？`)) return;

    try {
      setIsProcessing(true);
      await Promise.all(selectedFileIds.map(id => api.delete(`/archives/files/${id}`)));
      alert('删除成功');
      setSelectedFileIds([]);
      fetchFiles();
    } catch (error: any) {
      console.error('批量删除失败:', error);
      alert('部分素材删除失败');
    } finally {
      setIsProcessing(false);
    }
  };

  // 刷新记忆（语义合并）
  const handleConsolidate = async () => {
    if (!window.confirm('是否开始整理记忆？\n系统将自动分析并合并含义相同的重复节点。\n这可能需要几分钟时间。')) return;
    
    try {
      setIsConsolidating(true);
      setConsolidationProgress(0);
      const response: any = await api.post('/memory/consolidate');
      const { task_id } = response;
      
      // 轮询进度
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.get<TaskStatus>(`/memory/tasks/${task_id}`);
          setConsolidationProgress(status.progress);
          
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval);
            setIsConsolidating(false);
            if (status.status === 'completed') {
              // 刷新图谱
              window.location.reload(); 
            } else {
              alert('整理失败: ' + (status.message || status.error));
            }
          }
        } catch (e) {
          clearInterval(pollInterval);
          setIsConsolidating(false);
        }
      }, 1000);
      
    } catch (err: any) {
      console.error(err);
      setIsConsolidating(false);
      alert('无法启动整理任务');
    }
  };

  const handleClearMemory = async () => {
    if (!window.confirm('确定要清除所有记忆数据吗？此操作不可撤销。')) {
      return;
    }

    try {
      await api.delete('/memory/clear');
      alert('所有记忆已成功清除。');
      fetchStats();
    } catch (error: any) {
      console.error('清除记忆失败:', error);
      alert(`清除记忆失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const [showGraph, setShowGraph] = useState(true);

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
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
    
    // 如果是无效日期
    if (isNaN(date.getTime())) return dateStr;

    // 格式化为本地字符串，包含时间以增加精确度
    const options: Intl.DateTimeFormatOptions = { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    };
    
    if (diff < 24 * 3600 * 1000 && now.getDate() === date.getDate()) {
      return `今天 ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    if (diff < 48 * 3600 * 1000 && (now.getDate() - date.getDate() === 1 || now.getDate() - date.getDate() === -30)) {
      return `昨天 ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    
    return date.toLocaleString('zh-CN', options);
  };

  return (
    <div className="w-full min-h-screen flex flex-col animate-in fade-in duration-500 overflow-y-auto custom-scrollbar">
      {/* 顶部控制栏 */}
      <header className="flex-shrink-0 flex flex-col gap-[var(--md-sys-spacing-4)] p-[var(--md-sys-spacing-6)] border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface)] sticky top-0 z-30">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[var(--md-sys-typescale-display-small-size)] font-bold text-[var(--md-sys-color-on-background)]">
              记忆图谱
            </h1>
            <p className="text-[var(--md-sys-typescale-body-medium-size)] text-[var(--md-sys-color-on-surface-variant)]">
              可视化你的知识网络和思维关联
            </p>
          </div>
          
          <div className="flex items-center gap-[var(--md-sys-spacing-2)]">
            {isTraining && (
              <div className="flex flex-col items-end mr-4">
                <div className="flex items-center gap-2 text-[var(--md-sys-color-primary)] font-medium">
                  <Loader2 className="animate-spin" size={16} />
                  <span className="text-sm">{trainingMessage}</span>
                </div>
                <div className="w-48 h-1 bg-[var(--md-sys-color-surface-container-highest)] rounded-full mt-1 overflow-hidden">
                  <div 
                    className="h-full bg-[var(--md-sys-color-primary)] transition-all duration-500"
                    style={{ width: `${trainingProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="relative">
              <Button variant="outlined" icon={<Upload size={18} />} className="h-12 px-6">
                上传记忆
              </Button>
              <input 
                type="file" 
                className="absolute inset-0 opacity-0 cursor-pointer" 
                onChange={handleFileUpload} 
              />
            </div>
            
            <Button 
              variant="filled" 
              icon={<BrainCircuit size={18} />}
              loading={isTraining}
              onClick={handleTrainSelected}
              disabled={selectedFileIds.length === 0}
              className="h-12 px-6"
            >
              开始训练
            </Button>
            
            <Button
              variant={showGraph ? 'tonal' : 'outlined'}
              onClick={() => setShowGraph(!showGraph)}
              className="h-12 px-6"
            >
              {showGraph ? '隐藏图谱' : '显示图谱'}
            </Button>
            
            <button 
                onClick={handleConsolidate}
                disabled={isConsolidating}
                className="relative flex items-center justify-center gap-2 px-6 h-12 rounded-[var(--md-sys-shape-corner-full)] font-bold text-sm tracking-wide transition-all duration-200 active:scale-[0.97] disabled:opacity-40 disabled:pointer-events-none overflow-hidden group bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-md hover:shadow-lg"
            >
              <div className={`absolute inset-0 bg-white/20 translate-y-full transition-transform duration-300 ${isConsolidating ? 'translate-y-0' : 'group-hover:translate-y-0'}`} style={{ transform: isConsolidating ? `translateY(${100 - consolidationProgress}%)` : undefined }} />
              <span className={`transition-transform ${isConsolidating ? 'animate-spin' : 'group-hover:rotate-180'}`}>
                {isConsolidating ? <Loader2 size={18} /> : <RefreshCw size={18} />}
              </span>
              <span className="relative z-10">{isConsolidating ? `整理中 ${consolidationProgress}%` : '刷新记忆'}</span>
            </button>

            <Button
              variant="text"
              className="text-[var(--md-sys-color-error)] h-12 px-3"
              icon={<Trash2 size={18} />}
              onClick={handleClearMemory}
            >
              清除记忆
            </Button>
          </div>
        </div>

      </header>

      {/* 档案库管理区域 */}
      <section className="p-[var(--md-sys-spacing-6)] flex flex-col gap-[var(--md-sys-spacing-4)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-[var(--md-sys-spacing-4)] flex-1">
            <div className="flex items-center gap-[var(--md-sys-spacing-2)] p-1 bg-[var(--md-sys-color-surface-container-low)] rounded-[var(--md-sys-shape-corner-large)]">
              <button
                onClick={() => setViewMode('grid')}
                className={clsx(
                  "p-[var(--md-sys-spacing-2)] rounded-[var(--md-sys-shape-corner-medium)] transition-all",
                  viewMode === 'grid' ? "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] shadow-sm" : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                )}
              >
                <Grid size={18} />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={clsx(
                  "p-[var(--md-sys-spacing-2)] rounded-[var(--md-sys-shape-corner-medium)] transition-all",
                  viewMode === 'list' ? "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] shadow-sm" : "text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                )}
              >
                <List size={18} />
              </button>
            </div>

            <div className="relative flex-1 max-w-md group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--md-sys-color-on-surface-variant)] transition-colors group-focus-within:text-[var(--md-sys-color-primary)]" />
              <input
                type="text"
                placeholder="搜索素材文件名..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-10 pl-10 pr-4 rounded-[var(--md-sys-shape-corner-medium)] bg-[var(--md-sys-color-surface-container-high)] border-none text-sm text-[var(--md-sys-color-on-surface)] placeholder:text-[var(--md-sys-color-on-surface-variant)] focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none transition-all"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)]"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            <Button 
              variant="text" 
              onClick={handleSelectAll}
              icon={selectedFileIds.length === filteredFiles.length && filteredFiles.length > 0 ? <CheckSquare size={18} /> : <Square size={18} />}
              className="h-10 px-4"
            >
              {selectedFileIds.length === filteredFiles.length && filteredFiles.length > 0 ? '取消全选' : '全选素材'}
            </Button>

            {selectedFileIds.length > 0 && (
              <div className="flex items-center gap-[var(--md-sys-spacing-2)] animate-in fade-in slide-in-from-left-4">
                <div className="h-6 w-px bg-[var(--md-sys-color-outline-variant)] mx-2" />
                <span className="text-sm font-bold text-[var(--md-sys-color-primary)] mr-2">
                  已选 {selectedFileIds.length} 项
                </span>
                <Button 
                  variant="outlined" 
                  className="text-[var(--md-sys-color-error)] border-[var(--md-sys-color-error)] h-10 px-4"
                  icon={<Trash2 size={16} />}
                  onClick={handleBatchDelete}
                >
                  批量删除
                </Button>
                <Button 
                  variant="text" 
                  icon={<X size={16} />}
                  onClick={() => setSelectedFileIds([])}
                  className="h-10 px-4"
                >
                  取消
                </Button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            <Button variant="text" icon={<RefreshCw size={18} />} onClick={fetchFiles} loading={isLoadingFiles}>
              刷新列表
            </Button>
          </div>
        </div>

        {/* 文件列表/网格 */}
        <div className="min-h-[300px]">
          {isLoadingFiles ? (
            <div className="flex flex-col items-center justify-center py-20 opacity-50">
              <Loader2 size={48} className="animate-spin text-[var(--md-sys-color-primary)] mb-4" />
              <p>正在同步训练素材...</p>
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 bg-[var(--md-sys-color-surface-container-low)] rounded-[var(--md-sys-shape-corner-extra-large)] border-2 border-dashed border-[var(--md-sys-color-outline-variant)]/30">
              <Library size={64} className="text-[var(--md-sys-color-outline)] opacity-20 mb-4" />
              <p className="text-[var(--md-sys-color-on-surface-variant)]">暂无训练素材，请先上传</p>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-[var(--md-sys-spacing-4)]">
              {paginatedFiles.map((file) => {
                const Icon = fileTypeIcons[file.file_type] || fileTypeIcons.default;
                const isSelected = selectedFileIds.includes(file.id);
                return (
                  <GlassCard
                    key={file.id}
                    variant={isSelected ? "outlined" : "filled"}
                    padding="md"
                    hover
                    onClick={() => toggleFileSelection(file.id)}
                    className={clsx(
                      "flex flex-col gap-[var(--md-sys-spacing-3)] group cursor-pointer transition-all relative",
                      isSelected && "ring-2 ring-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-primary-container)]/10"
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className={clsx(
                        "w-12 h-12 rounded-[var(--md-sys-shape-corner-large)] flex items-center justify-center transition-transform group-hover:scale-110",
                        isSelected 
                          ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)]" 
                          : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)]"
                      )}>
                        {isSelected ? <CheckSquare size={24} /> : <Icon size={24} />}
                      </div>
                      <div className="flex items-center gap-1">
                        {file.original_name.toLowerCase().endsWith('.json') && !file.tags?.includes('split_result') && (
                          <button 
                            className="p-1 text-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-primary-container)] rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSplitFile(file.id);
                            }}
                          >
                            <Scissors size={16} />
                          </button>
                        )}
                        <button className="p-1 text-[var(--md-sys-color-outline)] hover:text-[var(--md-sys-color-on-surface)] opacity-0 group-hover:opacity-100">
                          <MoreVertical size={18} />
                        </button>
                      </div>
                    </div>
                    <div className="min-w-0">
                      <p className={clsx(
                        "text-[var(--md-sys-typescale-title-small-size)] font-bold truncate mb-1",
                        isSelected ? "text-[var(--md-sys-color-primary)]" : "text-[var(--md-sys-color-on-surface)]"
                      )}>
                        {file.original_name}
                      </p>
                      <p className="text-[var(--md-sys-typescale-label-small-size)] text-[var(--md-sys-color-on-surface-variant)] opacity-60">
                        {formatFileSize(file.file_size)} · {formatDate(file.created_at)}
                      </p>
                      <div className="mt-2 flex items-center gap-2">
                        <span className={clsx(
                          "px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider",
                          file.is_processed 
                            ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)]"
                            : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] opacity-70"
                        )}>
                          {file.is_processed ? '已训练' : '未训练'}
                        </span>
                      </div>
                    </div>
                  </GlassCard>
                );
              })}
            </div>
          ) : (
            <div className="bg-[var(--md-sys-color-surface-container-low)] rounded-[var(--md-sys-shape-corner-extra-large)] overflow-hidden">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-[var(--md-sys-color-surface-container-highest)]/30 text-[var(--md-sys-typescale-label-large-size)] text-[var(--md-sys-color-on-surface-variant)] uppercase">
                    <th className="text-left px-6 py-4 font-bold">名称</th>
                    <th className="text-left px-6 py-4 font-bold">类型</th>
                    <th className="text-left px-6 py-4 font-bold">大小</th>
                    <th className="text-left px-6 py-4 font-bold">创建日期</th>
                    <th className="text-left px-6 py-4 font-bold">状态</th>
                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--md-sys-color-outline-variant)]/20">
                  {paginatedFiles.map((file) => {
                    const Icon = fileTypeIcons[file.file_type] || fileTypeIcons.default;
                    const isSelected = selectedFileIds.includes(file.id);
                    return (
                      <tr 
                        key={file.id} 
                        onClick={() => toggleFileSelection(file.id)}
                        className={clsx(
                          "hover:bg-[var(--md-sys-color-surface-container-high)] transition-colors group cursor-pointer",
                          isSelected && "bg-[var(--md-sys-color-primary-container)]/20"
                        )}
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className={clsx(
                              "w-8 h-8 rounded-full flex items-center justify-center transition-all",
                              isSelected ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)]" : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)]"
                            )}>
                              {isSelected ? <CheckSquare size={16} /> : <Icon size={16} />}
                            </div>
                            <span className={clsx(
                              "text-sm font-bold",
                              isSelected ? "text-[var(--md-sys-color-primary)]" : "text-[var(--md-sys-color-on-surface)]"
                            )}>
                              {file.original_name}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-xs text-[var(--md-sys-color-on-surface-variant)]">{file.file_type}</td>
                        <td className="px-6 py-4 text-xs text-[var(--md-sys-color-on-surface-variant)]">{formatFileSize(file.file_size)}</td>
                        <td className="px-6 py-4 text-xs text-[var(--md-sys-color-on-surface-variant)]">{formatDate(file.created_at)}</td>
                        <td className="px-6 py-4">
                          <span className={clsx(
                            "px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
                            file.is_processed 
                              ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)]"
                              : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] opacity-70"
                          )}>
                            {file.is_processed ? '已训练' : '未训练'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                             {file.original_name.toLowerCase().endsWith('.json') && !file.tags?.includes('split_result') && (
                              <button 
                                className="p-1.5 text-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-primary-container)] rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSplitFile(file.id);
                                }}
                              >
                                <Scissors size={14} />
                              </button>
                            )}
                            <button className="p-2 text-[var(--md-sys-color-outline)] hover:text-[var(--md-sys-color-on-surface)] opacity-0 group-hover:opacity-100">
                              <MoreVertical size={18} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* 分页控制 */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between px-2">
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">
                显示 {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, filteredFiles.length)} / 共 {filteredFiles.length} 个素材
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg hover:bg-[var(--md-sys-color-surface-container-high)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={20} />
                </button>
                
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={clsx(
                          "w-8 h-8 rounded-lg text-xs font-bold transition-all",
                          currentPage === pageNum
                            ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-sm"
                            : "hover:bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)]"
                        )}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg hover:bg-[var(--md-sys-color-surface-container-high)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight size={20} />
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 知识图谱展示区域 - 无限画布重构 */}
      <section className={clsx('flex-1 relative min-h-[calc(100vh-140px)] flex flex-col', showGraph ? 'block' : 'hidden')}>
        
        {/* 核心画布容器 */}
        <div className="absolute inset-4 bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-extra-large)] overflow-hidden shadow-sm flex flex-col">
            
            {/* 顶部悬浮控制栏 - 绝对定位 */}
            <div className="absolute top-4 left-4 right-4 z-10 flex justify-between items-start pointer-events-none">
                
                {/* 左侧：标题与统计 */}
                <div className="pointer-events-auto bg-[var(--md-sys-color-surface-container-high)]/90 backdrop-blur-md px-4 py-2 rounded-full border border-[var(--md-sys-color-outline-variant)] shadow-sm flex items-center gap-4 transition-transform hover:scale-105">
                    <div className="flex items-center gap-2">
                        <BrainCircuit className="text-[var(--md-sys-color-primary)]" size={18} />
                        <span className="font-bold text-[var(--md-sys-color-on-surface)] text-sm">战略全景</span>
                    </div>
                    <div className="w-px h-4 bg-[var(--md-sys-color-outline-variant)]"></div>
                    <span className="text-xs text-[var(--md-sys-color-on-surface-variant)] font-mono">
                        {graphStats.nodes} NODES · {graphStats.links} LINKS
                    </span>
                </div>

                {/* 右侧：搜索与过滤 */}
                <div className="pointer-events-auto flex items-center gap-3">
                    {/* 搜索栏 */}
                    <div className="relative group">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Search className="h-4 w-4 text-[var(--md-sys-color-on-surface-variant)] group-focus-within:text-[var(--md-sys-color-primary)] transition-colors" />
                        </div>
                        <input
                            type="text"
                            placeholder="Search graph..."
                            className="w-48 focus:w-64 transition-all h-9 pl-9 pr-4 rounded-full bg-[var(--md-sys-color-surface-container-high)]/90 backdrop-blur-md border border-[var(--md-sys-color-outline-variant)] text-sm text-[var(--md-sys-color-on-surface)] placeholder:text-[var(--md-sys-color-on-surface-variant)] focus:ring-2 focus:ring-[var(--md-sys-color-primary)] focus:border-transparent outline-none shadow-sm"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    {/* 过滤器开关 */}
                    <div className="bg-[var(--md-sys-color-surface-container-high)]/90 backdrop-blur-md p-1 rounded-full border border-[var(--md-sys-color-outline-variant)] shadow-sm flex">
                         {nodeTypes.slice(0, 4).map(type => (
                             <button
                                key={type.key}
                                onClick={() => toggleType(type.key)}
                                className={clsx(
                                    "w-8 h-8 rounded-full flex items-center justify-center transition-all",
                                    selectedTypes.includes(type.key) 
                                        ? "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] shadow-inner" 
                                        : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)]"
                                )}
                                title={type.label}
                             >
                                 <type.icon size={14} />
                             </button>
                         ))}
                         <div className="w-px h-4 bg-[var(--md-sys-color-outline-variant)] mx-1 self-center"></div>
                         <button className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)]">
                            <Filter size={14} />
                         </button>
                    </div>
                </div>
            </div>

            {/* Pixi 画布 */}
            <div className="flex-1 w-full h-full relative bg-[var(--md-sys-color-surface)]">
                <StrategicPixiGraph />
            </div>
            
        </div>
      </section>
    </div>
  );
}
