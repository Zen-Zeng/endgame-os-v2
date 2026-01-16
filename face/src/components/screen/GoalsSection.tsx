import { useEffect, useState } from 'react';
import { 
  Target, 
  Briefcase, 
  Plus,
  ChevronRight,
  MoreVertical,
  Zap,
  Lock,
  Trash2
} from 'lucide-react';
import { api } from '../../lib/api';
import { useH3Store } from '../../stores/useH3Store';
import Button from '../ui/Button';
import CreateGoalModal from './CreateGoalModal';
import GoalDetailModal from './GoalDetailModal';
import clsx from 'clsx';

interface Goal {
  id: string;
  name: string;
  type: string;
  content: string;
  projects_count: number;
  projects: any[];
  dossier: {
    status: string;
    deadline?: string;
    priority: string;
    progress: number;
    created_at: string;
  };
}

interface GoalsSectionProps {
  className?: string;
}

/**
 * 目标管理组件 (Goals Section)
 * 集成在 Screen View 中，展示核心愿景与可执行目标
 */
export default function GoalsSection({ className }: GoalsSectionProps) {
  const { scores } = useH3Store();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  // 行动力指数
  const avgEnergy = (scores.mind + scores.body) / 2;
  const isEnergyLow = avgEnergy < 50;

  const fetchGoals = async () => {
    setLoading(true);
    try {
      const data = await api.get<any>('/memory/graph?view_type=strategic');
      // 过滤出 Goal 类型的节点
      const goalNodes = data.nodes.filter((n: any) => n.type === 'Goal');
      
      // 为每个 Goal 获取详情（包括关联项目数等）
      // 注意：这里的 api 设计可能需要优化，目前先这样实现
      const detailedGoals = await Promise.all(goalNodes.map(async (n: any) => {
        try {
          // 尝试获取子实体统计
          const subData = await api.get<any>(`/memory/lineage/${n.id}`); // 这里的 endpoint 可能不对，先用之前的逻辑占位
          return {
            ...n,
            projects_count: n.projects_count || 0,
            dossier: n.dossier || { priority: 'medium', status: 'active', progress: 0 }
          };
        } catch {
          return {
            ...n,
            projects_count: 0,
            dossier: { priority: 'medium', status: 'active', progress: 0 }
          };
        }
      }));
      
      setGoals(detailedGoals);
    } catch (err) {
      console.error('Failed to fetch goals:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteGoal = async (e: React.MouseEvent, goalId: string, goalName: string) => {
    e.stopPropagation();
    if (!window.confirm(`确定要删除目标 "${goalName}" 吗？此操作将同步删除知识图谱中的对应节点及其关联关系。`)) {
      return;
    }

    setIsDeleting(goalId);
    try {
      await api.delete(`/memory/nodes/${goalId}`);
      await fetchGoals();
    } catch (err) {
      console.error('Failed to delete goal:', err);
      alert('删除失败，请稍后重试');
    } finally {
      setIsDeleting(null);
    }
  };

  useEffect(() => {
    fetchGoals();
  }, []);

  return (
    <div className={clsx("flex flex-col gap-4", className)}>
      <div className="flex items-center justify-between px-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--md-sys-color-primary-container)] flex items-center justify-center text-[var(--md-sys-color-primary)]">
            <Target size={18} />
          </div>
          <h3 className="text-lg font-black">目标中枢 / GOALS</h3>
        </div>
        <div className={clsx(
          "flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider transition-colors",
          isEnergyLow ? "bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-error)]" : "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-primary)]"
        )}>
          {isEnergyLow ? <Lock size={12} /> : <Zap size={12} />}
          行动力: {Math.round(avgEnergy)}%
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array(3).fill(0).map((_, i) => (
            <div key={i} className="h-40 bg-[var(--md-sys-color-surface-container-high)] animate-pulse rounded-2xl" />
          ))
        ) : (
          <>
            {goals.map(goal => (
              <div key={goal.id} className="group p-4 bg-[var(--md-sys-color-surface)] rounded-2xl border border-[var(--md-sys-color-outline-variant)] hover:border-[var(--md-sys-color-primary)] transition-all shadow-sm">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-black uppercase px-2 py-0.5 bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] rounded-full">
                    {goal.dossier.priority}
                  </span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={(e) => handleDeleteGoal(e, goal.id, goal.name)}
                      disabled={isDeleting === goal.id}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-[var(--md-sys-color-outline)] hover:text-red-500 transition-colors"
                      title="删除目标"
                    >
                      {isDeleting === goal.id ? (
                        <div className="w-3.5 h-3.5 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                    <button className="p-1.5 rounded-lg hover:bg-[var(--md-sys-color-surface-variant)] transition-colors">
                      <MoreVertical size={14} className="text-[var(--md-sys-color-outline)]" />
                    </button>
                  </div>
                </div>
                
                <h4 className="text-sm font-bold mb-1 line-clamp-1">{goal.name}</h4>
                <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] line-clamp-2 mb-4 h-8">
                  {goal.content || "未定义详细愿景内容..."}
                </p>

                <div className="space-y-2">
                  <div className="flex justify-between text-[10px] opacity-60 font-bold uppercase">
                    <span>关联项目 ({goal.projects_count})</span>
                    <span>{goal.dossier.progress}%</span>
                  </div>
                  <div className="h-1 bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-[var(--md-sys-color-primary)] transition-all duration-500" 
                      style={{ width: `${goal.dossier.progress}%` }} 
                    />
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[var(--md-sys-color-outline-variant)] flex justify-between items-center">
                   <div className="w-6 h-6 rounded-full bg-[var(--md-sys-color-tertiary-container)] flex items-center justify-center text-[var(--md-sys-color-on-tertiary-container)]">
                      <Briefcase size={12} />
                   </div>
                   <button 
                    onClick={() => {
                      setSelectedGoal(goal);
                      setIsDetailModalOpen(true);
                    }}
                    className="text-[10px] font-bold text-[var(--md-sys-color-primary)] flex items-center gap-1 hover:underline"
                   >
                    详情 <ChevronRight size={12} />
                   </button>
                </div>
              </div>
            ))}
            
            {/* 快速创建 */}
            <button 
              onClick={() => setIsCreateModalOpen(true)}
              className="h-full min-h-[160px] border-2 border-dashed border-[var(--md-sys-color-outline-variant)] rounded-2xl flex flex-col items-center justify-center gap-2 hover:bg-[var(--md-sys-color-primary)]/5 transition-colors group"
            >
              <Plus size={24} className="text-[var(--md-sys-color-outline)] group-hover:text-[var(--md-sys-color-primary)] transition-colors" />
              <span className="text-xs font-bold text-[var(--md-sys-color-outline)] group-hover:text-[var(--md-sys-color-primary)]">添加目标</span>
            </button>
          </>
        )}
      </div>

      <CreateGoalModal 
        isOpen={isCreateModalOpen} 
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={fetchGoals}
      />

      <GoalDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedGoal(null);
        }}
        goal={selectedGoal}
      />
    </div>
  );
}
