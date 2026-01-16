import { useState, useEffect } from 'react';
import { 
  Target, 
  Share2, 
  RefreshCw,
  Globe,
  Users,
  Compass,
  GitBranch,
  Trash2
} from 'lucide-react';
import StrategicPixiGraph from '../graph/StrategicPixiGraph';
import StrategicTreeView from '../graph/StrategicTreeView';
import Button from '../ui/Button';
import { api } from '../../lib/api';
import clsx from 'clsx';

interface GraphStats {
  nodes: number;
  links: number;
  typeCounts: Record<string, number>;
}

interface GraphResponse {
  nodes: any[];
  links: any[];
  total_nodes: number;
  total_links: number;
  type_counts: Record<string, number>;
}

interface MemoryGraphProps {
  className?: string;
}

export default function MemoryGraph({ className }: MemoryGraphProps) {
  const [graphViewType, setGraphViewType] = useState<'global' | 'strategic' | 'people' | 'staging'>('strategic');
  const [graphRefreshKey, setGraphRefreshKey] = useState(0);
  const [layoutMode, setLayoutMode] = useState<'compass' | 'tree'>('compass');
  const [graphStats, setGraphStats] = useState<GraphStats>({ nodes: 0, links: 0, typeCounts: {} });
  const [isDeleting, setIsDeleting] = useState(false);
  
  // 语义对齐过滤器状态 (Phase 4)
  const [alignmentThreshold, setAlignmentThreshold] = useState(0.0);
  const [showImplicitLinks, setShowImplicitLinks] = useState(false);

  // 获取图谱统计数据
  const fetchStats = async () => {
    try {
      const response = await api.get<GraphResponse>('/memory/graph');
      
      setGraphStats({
        nodes: response.total_nodes || 0,
        links: response.total_links || 0,
        typeCounts: response.type_counts || {}
      });
    } catch (error) {
      console.error('获取图谱统计失败:', error);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [graphRefreshKey]);

  const refreshGraph = () => {
    setGraphRefreshKey(prev => prev + 1);
  };

  const handleClearMemory = async () => {
    if (!window.confirm('确定要清空所有记忆数据吗？此操作不可撤销。')) {
      return;
    }

    try {
      setIsDeleting(true);
      await api.delete('/memory/clear');
      refreshGraph();
    } catch (error) {
      console.error('清空记忆失败:', error);
      alert('清空记忆失败，请重试');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className={clsx("flex flex-col h-full bg-[var(--md-sys-color-surface-container-low)] rounded-[var(--md-sys-shape-corner-extra-large)] overflow-hidden border border-[var(--md-sys-color-outline-variant)]", className)}>
      {/* 图谱控制栏 */}
      <div className="flex flex-wrap items-center justify-between p-4 border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface)] gap-4">
        <div className="flex items-center gap-2">
          <div className="flex bg-[var(--md-sys-color-surface-container-high)] p-1 rounded-full">
            <button
              onClick={() => setGraphViewType('strategic')}
              className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all",
                graphViewType === 'strategic' 
                  ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-sm" 
                  : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
              )}
            >
              <Target size={14} />
              战略指南针
            </button>
            <button
              onClick={() => setGraphViewType('global')}
              className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all",
                graphViewType === 'global' 
                  ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-sm" 
                  : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
              )}
            >
              <Globe size={14} />
              全局图谱
            </button>
            <button
              onClick={() => setGraphViewType('people')}
              className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all",
                graphViewType === 'people' 
                  ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-sm" 
                  : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
              )}
            >
              <Users size={14} />
              人际网络
            </button>
          </div>

          <div className="h-4 w-[1px] bg-[var(--md-sys-color-outline-variant)] mx-2" />

          <div className="flex bg-[var(--md-sys-color-surface-container-high)] p-1 rounded-full">
            <button
              onClick={() => setLayoutMode('compass')}
              className={clsx(
                "p-1.5 rounded-full transition-all",
                layoutMode === 'compass' 
                  ? "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)]" 
                  : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
              )}
              title="指南针布局"
            >
              <Compass size={16} />
            </button>
            <button
              onClick={() => setLayoutMode('tree')}
              className={clsx(
                "p-1.5 rounded-full transition-all",
                layoutMode === 'tree' 
                  ? "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)]" 
                  : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
              )}
              title="树状布局"
            >
              <GitBranch size={16} />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 详细统计 breakdown */}
          <div className="hidden lg:flex items-center gap-4 text-[10px] font-black uppercase tracking-tighter text-[var(--md-sys-color-on-surface-variant)] mr-4 opacity-70 border-r border-[var(--md-sys-color-outline-variant)] pr-4">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--md-sys-color-error)]"></span>
              愿景 {graphStats.typeCounts['Vision'] || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--md-sys-color-tertiary)]"></span>
              目标 {graphStats.typeCounts['Goal'] || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--md-sys-color-secondary)]"></span>
              项目 {graphStats.typeCounts['Project'] || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--md-sys-color-outline)]"></span>
              任务 {graphStats.typeCounts['Task'] || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--md-sys-color-primary)]"></span>
              人 {graphStats.typeCounts['Person'] || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--md-sys-color-outline)]"></span>
              组织 {graphStats.typeCounts['Organization'] || 0}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-3 text-xs font-bold text-[var(--md-sys-color-on-surface-variant)] mr-2">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[var(--md-sys-color-primary)]"></span>
              {graphStats.nodes} 总节点
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[var(--md-sys-color-outline)]"></span>
              {graphStats.links} 连线
            </span>
          </div>
          
          <Button
            variant="text"
            icon={<RefreshCw size={16} />}
            onClick={refreshGraph}
          >
            刷新
          </Button>

          <Button
            variant="text"
            className="text-[var(--md-sys-color-error)] hover:bg-[var(--md-sys-color-error-container)] hover:text-[var(--md-sys-color-on-error-container)]"
            icon={<Trash2 size={16} />}
            onClick={handleClearMemory}
            disabled={isDeleting}
          >
            {isDeleting ? '正在清空...' : '清空记忆'}
          </Button>
        </div>
      </div>

      {/* 图谱画布区域 */}
      <div className="flex-1 relative overflow-hidden">
        {layoutMode === 'compass' ? (
          <StrategicPixiGraph 
            viewType={graphViewType}
            refreshKey={graphRefreshKey}
            alignmentThreshold={alignmentThreshold}
            showImplicitLinks={showImplicitLinks}
          />
        ) : (
          <StrategicTreeView 
            alignmentThreshold={alignmentThreshold}
            refreshKey={graphRefreshKey}
          />
        )}
        
        {/* 浮动过滤器 (Phase 4) */}
        <div className="absolute bottom-6 right-6 p-4 bg-[var(--md-sys-color-surface)]/80 backdrop-blur-md rounded-2xl border border-[var(--md-sys-color-outline-variant)] shadow-lg z-10 max-w-xs space-y-3">
          <div className="flex items-center justify-between gap-8">
            <span className="text-xs font-bold text-[var(--md-sys-color-on-surface)]">语义对齐阈值</span>
            <span className="text-xs font-mono font-bold text-[var(--md-sys-color-primary)]">{(alignmentThreshold * 100).toFixed(0)}%</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            value={alignmentThreshold}
            onChange={(e) => setAlignmentThreshold(parseFloat(e.target.value))}
            className="w-full accent-[var(--md-sys-color-primary)]"
          />
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs font-bold text-[var(--md-sys-color-on-surface)]">显示隐性关联</span>
            <button 
              onClick={() => setShowImplicitLinks(!showImplicitLinks)}
              className={clsx(
                "w-10 h-5 rounded-full p-1 transition-colors duration-200",
                showImplicitLinks ? "bg-[var(--md-sys-color-primary)]" : "bg-[var(--md-sys-color-outline)]"
              )}
            >
              <div className={clsx(
                "w-3 h-3 bg-white rounded-full transition-transform duration-200",
                showImplicitLinks ? "translate-x-5" : "translate-x-0"
              )} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
