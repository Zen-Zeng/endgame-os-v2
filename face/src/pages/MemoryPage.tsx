/**
 * 记忆图谱页面
 * 优化后的知识图谱可视化
 */
import { useState, useEffect } from 'react';
import { Search, Filter, ZoomIn, ZoomOut, Maximize2, RefreshCw, Upload, BrainCircuit, Trash2 } from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import MemoryGraph from '../components/MemoryGraph';
import api from '../lib/api';
import clsx from 'clsx';

interface GraphStats {
  nodes: number;
  links: number;
}

// 节点类型配置
const nodeTypes = [
  { key: 'User', label: '用户', color: '#FF6B6B' },
  { key: 'Goal', label: '目标', color: '#4ECDC4' },
  { key: 'Project', label: '项目', color: '#45B7D1' },
  { key: 'Task', label: '任务', color: '#96CEB4' },
  { key: 'Log', label: '日志', color: '#FFEAA7' },
  { key: 'Concept', label: '概念', color: '#DDA0DD' },
];

export default function MemoryPage() {
  const [showGraph, setShowGraph] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [graphStats, setGraphStats] = useState<GraphStats>({ nodes: 0, links: 0 });
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState<number | null>(null);

  // 获取图谱统计数据
  const fetchStats = async () => {
    try {
      setIsLoadingStats(true);
      const data = await api.get<{nodes: any[], links: any[]}>('/memory/graph');
      setGraphStats({
        nodes: data.nodes?.length || 0,
        links: data.links?.length || 0,
      });
    } catch (error) {
      console.error('获取图谱统计失败:', error);
    } finally {
      setIsLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [showGraph]); // 当显示图谱时重新获取

  const handleTrain = async () => {
    try {
      setIsTraining(true);
      setTrainingProgress(0);
      
      // 1. 获取最近上传的文件
      const files: any = await api.get('/archives/files');
      if (!files || files.length === 0) {
        alert('档案库中没有可训练的文件，请先上传。');
        setIsTraining(false);
        return;
      }

      // 2. 触发训练 (使用第一个文件作为示例，实际可让用户选择)
      const latestFile = files[0];
      const trainResponse: any = await api.post('/memory/train', { 
        filename: latestFile.filename 
      });
      
      const taskId = trainResponse.task_id;
      
      // 3. 轮询进度
      const timer = setInterval(async () => {
        try {
          const status: any = await api.get(`/memory/tasks/${taskId}`);
          setTrainingProgress(status.progress);
          
          if (status.status === 'completed') {
            clearInterval(timer);
            setIsTraining(false);
            setTrainingProgress(null);
            fetchStats(); // 刷新统计
            alert('记忆训练完成！');
          } else if (status.status === 'failed') {
            clearInterval(timer);
            setIsTraining(false);
            setTrainingProgress(null);
            alert(`训练失败: ${status.error}`);
          }
        } catch (err) {
          clearInterval(timer);
          setIsTraining(false);
        }
      }, 2000);

    } catch (error) {
      console.error('训练启动失败:', error);
      setIsTraining(false);
      alert('训练启动失败，请检查后端服务。');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 前端预检文件大小 (100MB)
    const MAX_SIZE = 100 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      alert(`文件太大 (${(file.size / 1024 / 1024).toFixed(2)}MB)，请上传 100MB 以内的文件。`);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/archives/upload', formData);
      alert('文件上传成功，现在可以开始训练。');
    } catch (error: any) {
      console.error('上传失败:', error);
      // 提取后端返回的详细错误信息
      const detail = error.response?.data?.detail || error.message || '未知错误';
      alert(`上传失败: ${detail}`);
    }
  };

  const handleClearMemory = async () => {
    if (!window.confirm('确定要清除所有记忆数据吗？此操作不可撤销，系统将丢失所有已学习的知识、关联和历史记录。')) {
      return;
    }

    try {
      await api.delete('/memory/clear');
      alert('所有记忆已成功清除。');
      // 强制图谱刷新
      if (showGraph) {
        // 这里可以通过触发重新渲染或调用 MemoryGraph 的刷新方法
        window.location.reload(); 
      }
    } catch (error: any) {
      console.error('清除记忆失败:', error);
      alert(`清除记忆失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  return (
    <div className="h-screen flex flex-col">
      {/* 页面标题 */}
      <header className="flex-shrink-0 px-8 py-6 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="font-display text-2xl font-bold text-[var(--color-text-primary)]">
              记忆图谱
            </h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              可视化你的知识网络和思维关联
            </p>
          </div>
          <div className="flex gap-2">
            <label className="btn btn-secondary cursor-pointer">
              <Upload size={18} />
              <span>上传记忆</span>
              <input type="file" className="hidden" onChange={handleFileUpload} />
            </label>
            <button
              onClick={handleTrain}
              disabled={isTraining}
              className={clsx(
                'btn btn-primary',
                isTraining && 'opacity-50 cursor-not-allowed'
              )}
            >
              <BrainCircuit size={18} />
              {isTraining ? `训练中 ${trainingProgress}%` : '开始训练'}
            </button>
            <button
              onClick={() => setShowGraph(!showGraph)}
              className={clsx(
                'btn',
                showGraph ? 'btn-primary' : 'btn-secondary'
              )}
            >
              {showGraph ? '隐藏图谱' : '显示图谱'}
            </button>
            <button
              onClick={handleClearMemory}
              className="btn bg-red-500/10 hover:bg-red-500/20 text-red-500 border-red-500/20"
              title="清除所有记忆数据"
            >
              <Trash2 size={18} />
              <span>清除记忆</span>
            </button>
          </div>
        </div>

        {/* 搜索和过滤 */}
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="搜索记忆节点..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full pl-12"
            />
          </div>
          
          {/* 类型过滤 */}
          <div className="flex items-center gap-2">
            <Filter size={18} className="text-[var(--color-text-muted)]" />
            {nodeTypes.map((type) => (
              <button
                key={type.key}
                onClick={() => toggleType(type.key)}
                className={clsx(
                  'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                  selectedTypes.includes(type.key)
                    ? 'text-white'
                    : 'text-[var(--color-text-secondary)] bg-[var(--color-bg-card)] hover:bg-[var(--color-bg-card-hover)]'
                )}
                style={{
                  backgroundColor: selectedTypes.includes(type.key)
                    ? type.color
                    : undefined,
                }}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 图谱区域 */}
        <div className={clsx('flex-1 relative', showGraph ? 'block' : 'hidden lg:block')}>
          {showGraph ? (
            <MemoryGraph onClose={() => setShowGraph(false)} />
          ) : (
            // 占位状态
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-24 h-24 rounded-2xl bg-[var(--color-primary-alpha-20)] flex items-center justify-center mb-6">
                <svg
                  viewBox="0 0 100 100"
                  className="w-16 h-16 text-[var(--color-primary)]"
                >
                  <circle cx="30" cy="30" r="8" fill="currentColor" opacity="0.6" />
                  <circle cx="70" cy="30" r="8" fill="currentColor" opacity="0.8" />
                  <circle cx="50" cy="70" r="10" fill="currentColor" />
                  <line
                    x1="30"
                    y1="30"
                    x2="70"
                    y2="30"
                    stroke="currentColor"
                    strokeWidth="2"
                    opacity="0.4"
                  />
                  <line
                    x1="30"
                    y1="30"
                    x2="50"
                    y2="70"
                    stroke="currentColor"
                    strokeWidth="2"
                    opacity="0.4"
                  />
                  <line
                    x1="70"
                    y1="30"
                    x2="50"
                    y2="70"
                    stroke="currentColor"
                    strokeWidth="2"
                    opacity="0.4"
                  />
                </svg>
              </div>
              <h2 className="font-display text-xl font-semibold text-[var(--color-text-primary)] mb-2">
                记忆图谱
              </h2>
              <p className="text-[var(--color-text-secondary)] mb-6 max-w-md">
                点击"显示图谱"按钮，探索你的知识网络和思维关联
              </p>
              <button
                onClick={() => setShowGraph(true)}
                className="btn btn-primary"
              >
                显示图谱
              </button>
            </div>
          )}

          {/* 图谱控制按钮 */}
          {showGraph && (
            <div className="absolute top-4 right-4 flex flex-col gap-2">
              <button className="p-2 rounded-lg bg-[var(--color-bg-card)] border border-[var(--color-border)] hover:bg-[var(--color-bg-card-hover)] transition-colors">
                <ZoomIn size={18} className="text-[var(--color-text-primary)]" />
              </button>
              <button className="p-2 rounded-lg bg-[var(--color-bg-card)] border border-[var(--color-border)] hover:bg-[var(--color-bg-card-hover)] transition-colors">
                <ZoomOut size={18} className="text-[var(--color-text-primary)]" />
              </button>
              <button className="p-2 rounded-lg bg-[var(--color-bg-card)] border border-[var(--color-border)] hover:bg-[var(--color-bg-card-hover)] transition-colors">
                <Maximize2 size={18} className="text-[var(--color-text-primary)]" />
              </button>
              <button className="p-2 rounded-lg bg-[var(--color-bg-card)] border border-[var(--color-border)] hover:bg-[var(--color-bg-card-hover)] transition-colors">
                <RefreshCw size={18} className="text-[var(--color-text-primary)]" />
              </button>
            </div>
          )}
        </div>

        {/* 侧边信息面板 */}
        <div className="w-80 border-l border-[var(--color-border)] p-6 overflow-y-auto hidden lg:block">
          {/* 统计信息 */}
          <GlassCard className="mb-6">
            <h3 className="font-medium text-[var(--color-text-primary)] mb-4">
              图谱统计
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-2xl font-bold text-[var(--color-primary)]">
                  {isLoadingStats ? '...' : graphStats.nodes}
                </p>
                <p className="text-xs text-[var(--color-text-muted)]">节点数</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-[var(--color-primary)]">
                  {isLoadingStats ? '...' : graphStats.links}
                </p>
                <p className="text-xs text-[var(--color-text-muted)]">关系数</p>
              </div>
            </div>
          </GlassCard>

          {/* 图例 */}
          <GlassCard className="mb-6">
            <h3 className="font-medium text-[var(--color-text-primary)] mb-4">
              图例
            </h3>
            <div className="space-y-2">
              {nodeTypes.map((type) => (
                <div key={type.key} className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: type.color }}
                  />
                  <span className="text-sm text-[var(--color-text-secondary)]">
                    {type.label}
                  </span>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* 最近访问 */}
          <GlassCard>
            <h3 className="font-medium text-[var(--color-text-primary)] mb-4">
              最近访问
            </h3>
            <div className="space-y-3">
              {['成为独立开发者', 'Endgame OS', '完成 MVP'].map((item, index) => (
                <div
                  key={index}
                  className="p-2 rounded-lg hover:bg-[var(--color-bg-card-hover)] cursor-pointer transition-colors"
                >
                  <p className="text-sm text-[var(--color-text-primary)]">
                    {item}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    刚刚
                  </p>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

