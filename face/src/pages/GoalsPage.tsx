/**
 * Endgame OS v2 - Goals Management Page
 * Vision -> Goal -> Project -> Task mapping with H3 Energy Integration
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Target, 
  Flag, 
  Briefcase, 
  CheckCircle2, 
  Lock, 
  Zap, 
  Plus,
  AlertCircle,
  ChevronRight,
  MoreVertical
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import Button from '../components/ui/Button';
import { useH3Store } from '../stores/useH3Store';
import { api } from '../lib/api';
import { clsx } from 'clsx';

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
  };
}

export default function GoalsPage() {
  const navigate = useNavigate();
  const { scores = { mind: 0, body: 0, spirit: 0, vocation: 0 } } = useH3Store();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);

  // 计算平均心智和身体能量
  const avgEnergy = (scores.mind + scores.body) / 2;
  const isEnergyLow = avgEnergy < 50;

  useEffect(() => {
    fetchGoals();
  }, []);

  const fetchGoals = async () => {
    try {
      setLoading(true);
      const data = await api.get<Goal[]>('/goals/list');
      setGoals(data || []);
    } catch (e) {
      console.error('Fetch goals error', e);
    } finally {
      setLoading(false);
    }
  };

  const handleTaskAction = (intensity: number) => {
    if (intensity >= 4 && isEnergyLow) {
      setError({
        title: "能量锁定",
        message: "当前身体/心智能量过低，系统已锁定高强度任务以防止过度损耗。",
        type: "lock"
      });
      return;
    }
    // 执行任务操作...
  };

  return (
    <div className="page-container space-y-[var(--md-sys-spacing-4)] pb-20">
      <header className="flex justify-between items-end py-[var(--md-sys-spacing-3)]">
        <div>
          <h1 className="text-[var(--md-sys-typescale-display-medium-size)] font-bold text-[var(--md-sys-color-on-background)]">目标管理</h1>
          <p className="text-[var(--md-sys-color-on-surface-variant)] opacity-70">将愿景转化为可执行的神经节点</p>
        </div>
        <Button variant="filled" icon={<Plus size={18} />}>创建新愿景</Button>
      </header>

      {/* 能量状态条 - 联动显示 */}
      <GlassCard className={clsx(
        "border-l-4 transition-all duration-500",
        isEnergyLow ? "border-l-[var(--md-sys-color-error)]" : "border-l-[var(--md-sys-color-primary)]"
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={clsx(
              "p-3 rounded-full",
              isEnergyLow ? "bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-error)]" : "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-primary)]"
            )}>
              {isEnergyLow ? <Lock size={24} /> : <Zap size={24} />}
            </div>
            <div>
              <div className="text-[var(--md-sys-typescale-title-medium-size)] font-bold">
                当前行动力指数: {Math.round(avgEnergy)}%
              </div>
              <p className="text-sm opacity-70">
                {isEnergyLow ? "建议优先进行低强度任务或能量校准" : "能量充足，适合处理高挑战任务"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <div className="text-center px-4">
              <div className="text-xs uppercase opacity-50">Mind</div>
              <div className="font-mono font-bold">{scores.mind}%</div>
            </div>
            <div className="text-center px-4">
              <div className="text-xs uppercase opacity-50">Body</div>
              <div className="font-mono font-bold">{scores.body}%</div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* 错误提示弹窗 - 能量锁定视觉效果 */}
      {error && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-300">
          <GlassCard className="max-w-md border-[var(--md-sys-color-error)] shadow-2xl shadow-error/20" padding="lg">
            <div className="text-center space-y-4">
              <div className="inline-block p-4 bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-error)] rounded-full animate-pulse">
                <Lock size={48} />
              </div>
              <h2 className="text-2xl font-bold text-[var(--md-sys-color-error)]">{error.title}</h2>
              <p className="text-[var(--md-sys-color-on-surface-variant)]">{error.message}</p>
              <div className="flex gap-3 justify-center mt-6">
                <Button variant="tonal" onClick={() => navigate('/calibration')}>前往校准</Button>
                <Button variant="filled" onClick={() => setError(null)}>确认</Button>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* 目标列表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-[var(--md-sys-spacing-3)]">
        {loading ? (
          Array(3).fill(0).map((_, i) => (
            <div key={i} className="h-64 bg-surface-variant/20 animate-pulse rounded-2xl" />
          ))
        ) : (
          goals.map(goal => (
            <GlassCard key={goal.id} variant="elevated" className="group hover:ring-2 ring-[var(--md-sys-color-primary)] transition-all">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] rounded-lg">
                  <Target size={20} />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase px-2 py-1 bg-surface-variant rounded-full opacity-70">
                    {goal.dossier.priority}
                  </span>
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <MoreVertical size={16} />
                  </button>
                </div>
              </div>
              
              <h3 className="text-[var(--md-sys-typescale-title-large-size)] font-bold mb-2">{goal.name}</h3>
              <p className="text-sm text-[var(--md-sys-color-on-surface-variant)] line-clamp-2 mb-6">
                {goal.content || "未定义详细愿景内容..."}
              </p>

              <div className="space-y-3">
                <div className="flex justify-between text-xs opacity-60 font-bold uppercase tracking-wider">
                  <span>关联项目 ({goal.projects_count})</span>
                  <span>进度 0%</span>
                </div>
                <div className="h-1.5 bg-surface-variant rounded-full overflow-hidden">
                  <div className="h-full bg-[var(--md-sys-color-primary)] w-[15%]" />
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-surface-variant/30 flex justify-between items-center">
                <div className="flex -space-x-2">
                   {/* 这里可以循环显示子任务的小图标 */}
                   <div className="w-8 h-8 rounded-full bg-[var(--md-sys-color-tertiary-container)] border-2 border-[var(--md-sys-color-surface)] flex items-center justify-center text-[var(--md-sys-color-on-tertiary-container)]">
                      <Briefcase size={14} />
                   </div>
                </div>
                <Button variant="text" icon={<ChevronRight size={16} />}>查看详情</Button>
              </div>
            </GlassCard>
          ))
        )}
        
        {/* 快速创建卡片 */}
        <button className="h-full min-h-[240px] border-2 border-dashed border-surface-variant rounded-3xl flex flex-col items-center justify-center gap-3 hover:bg-surface-variant/10 transition-colors group">
          <div className="p-4 rounded-full bg-surface-variant/20 group-hover:scale-110 transition-transform">
            <Plus size={32} className="opacity-40" />
          </div>
          <span className="font-bold opacity-40">添加新目标</span>
        </button>
      </div>
    </div>
  );
}
