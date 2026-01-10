/**
 * Endgame OS v2 - Dashboard Page
 * AI-Summary Header | Reminders | Vision | Goals | H3 Energy | Activity Logs
 */
import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  MessageSquare,
  Target,
  Zap,
  ChevronRight,
  Flag,
  Coffee,
  Moon,
  Calendar,
  PieChart,
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import Button from '../components/ui/Button';
import { useAuthStore } from '../stores/useAuthStore';
import { useH3Store } from '../stores/useH3Store';
import { api } from '../lib/api';
import Slider from '../components/ui/Slider';
import type { H3Scores } from '../stores/useH3Store';

// H3 维度配置
const h3Dimensions = [
  { key: 'mind' as keyof H3Scores, label: '心智', color: 'var(--md-sys-color-primary)', icon: '🧠' },
  { key: 'body' as keyof H3Scores, label: '身体', color: '#aaddbf', icon: '💪' },
  { key: 'spirit' as keyof H3Scores, label: '精神', color: '#ffb4a9', icon: '✨' },
  { key: 'vocation' as keyof H3Scores, label: '志业', color: '#a8c7fa', icon: '🎯' },
] as const;

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { scores, fetchCurrentState } = useH3Store();
  
  // 本地暂存的 H3 分数，用于点击调整
  const [localScores, setLocalScores] = useState(scores);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [data, setData] = useState<any>({
    stats: {
      total_conversations: 0,
      streak_days: 0,
      total_goals: 0,
      completed_goals: 0,
      today_messages: 0,
      today_calibrations: 0
    },
    recent_activities: [],
    active_goals: [],
    ai_summary: '正在生成系统实时概览...',
    vision: {
      title: '终局愿景',
      description: '',
      progress: 0
    }
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get<any>('/dashboard/overview');
        if (response) {
          setData(response);
        }
      } catch (e) {
        console.error('Fetch dashboard error', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    fetchCurrentState(); // 强制刷新全局 H3 状态
  }, [fetchCurrentState]);

  // 当全局分数更新时，同步本地分数
  useEffect(() => {
    setLocalScores(scores);
  }, [scores]);

  const h3Total = Math.round(((localScores?.mind || 0) + (localScores?.body || 0) + (localScores?.spirit || 0) + (localScores?.vocation || 0)) / 4);
  const displayName = user?.name || '岳';
  
  // 生成数字分身问候语
  const fullGreeting = useMemo(() => {
    const now = new Date();
    const hour = now.getHours();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const date = now.getDate();
    const dayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const dayName = dayNames[now.getDay()];
    
    let timeGreeting = '';
    if (hour < 5) timeGreeting = '深夜好';
    else if (hour < 11) timeGreeting = '早上好';
    else if (hour < 13) timeGreeting = '中午好';
    else if (hour < 18) timeGreeting = '下午好';
    else timeGreeting = '晚上好';

    const futureMessages = [
      '你的未来版本正在观察此刻的决策，保持对齐。',
      '每一个当下的刻意练习，都在重塑终局的轮廓。',
      '检测到时间线平稳，今日是推进核心愿景的绝佳窗口。',
      '记住，系统存在的意义是放大你的意志，而非替代你的思考。',
      '在复杂的世界中，保持对终局愿景的极简专注。',
      '数据回传显示：你今天的专注度将决定下周的自由度。',
      '欢迎回到指挥中心，心智引擎已就绪。'
    ];
    const randomFutureMsg = futureMessages[Math.floor(Math.random() * futureMessages.length)];
    
    return `${displayName}，${timeGreeting}。今天是 ${year}年${month}月${date}日${dayName}，${randomFutureMsg}`;
  }, [displayName]);

  // 格式化相对时间
  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return date.toLocaleDateString();
  };

  // 今日提醒逻辑
  const reminder = useMemo(() => {
    const now = new Date();
    const hour = now.getHours();
    const day = now.getDay(); // 0 是周日
    const isLastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate() === now.getDate();

    // 优先级：月审计 > 周盘点 > 日复盘 > 日启动
    if (isLastDayOfMonth && hour >= 18) {
      return {
        type: 'monthly',
        title: '月度系统审计',
        desc: '本月终局对齐度评估，重新校准长期航线',
        icon: <PieChart size={28} />,
        color: 'var(--md-sys-color-tertiary)'
      };
    }
    if (day === 0 && hour >= 18) {
      return {
        type: 'weekly',
        title: '周中枢盘点',
        desc: '回顾本周进展，规划下周核心突破点',
        icon: <Calendar size={28} />,
        color: 'var(--md-sys-color-secondary)'
      };
    }
    if (hour >= 17) {
      return {
        type: 'evening',
        title: '日终复盘',
        desc: '记录今日洞察，清理认知缓存',
        icon: <Moon size={28} />,
        color: 'var(--md-sys-color-primary)'
      };
    }
    if (hour >= 8) {
      return {
        type: 'morning',
        title: '日启动协议',
        desc: '同步终局愿景，锁定今日 Critical Task',
        icon: <Coffee size={28} />,
        color: 'var(--md-sys-color-primary)'
      };
    }
    return null;
  }, []);

  const handleScoreChange = (key: keyof typeof scores, val: number[]) => {
    setLocalScores(prev => ({ ...prev, [key]: val[0] }));
  };

  const handleCalibrate = async () => {
    setIsCalibrating(true);
    try {
      // 使用 store 的 updateScores 确保全局状态同步更新
      await useH3Store.getState().updateScores(localScores, '手动校准', 'manual');
      
      // 刷新仪表盘统计数据
      const response = await api.get<any>('/dashboard/overview');
      if (response) setData(response);
    } catch (e) {
      console.error('Calibration failed', e);
    } finally {
      setIsCalibrating(false);
    }
  };

  return (
    <div className="page-container space-y-[var(--md-sys-spacing-6)] pb-20">
      {/* 1. HEADER - AI Summary & Stats Integrated */}
      <header className="py-[var(--md-sys-spacing-4)] space-y-[var(--md-sys-spacing-4)]">
        <h1 className="text-[var(--md-sys-typescale-display-small-size)] font-bold text-[var(--md-sys-color-on-background)] max-w-4xl">
          {fullGreeting}
        </h1>
        
        <div className="flex gap-10 items-center">
          <div>
            <p className="text-[var(--md-sys-typescale-label-medium-size)] opacity-50 uppercase tracking-tighter">对齐天数</p>
            <p className="text-[var(--md-sys-typescale-title-large-size)] font-black text-[var(--md-sys-color-primary)]">{data.stats?.streak_days || 0}</p>
          </div>
          <div>
            <p className="text-[var(--md-sys-typescale-label-medium-size)] opacity-50 uppercase tracking-tighter">对话</p>
            <p className="text-[var(--md-sys-typescale-title-large-size)] font-black">{data.stats?.total_messages || 0}</p>
          </div>
          <div>
            <p className="text-[var(--md-sys-typescale-label-medium-size)] opacity-50 uppercase tracking-tighter">能量点</p>
            <p className="text-[var(--md-sys-typescale-title-large-size)] font-black text-[var(--md-sys-color-secondary)]">{data.stats?.energy_points || 0}</p>
          </div>
        </div>

        <div className="max-w-3xl pt-2">
          <p className="text-[var(--md-sys-typescale-headline-small-size)] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed opacity-90 italic">
            「{String(data.ai_summary || '').includes('。') ? String(data.ai_summary || '').split('。').slice(1).join('。') : String(data.ai_summary || '')}」
          </p>
        </div>
      </header>

      {/* 2. TODAY REMINDERS */}
      {reminder && (
        <section className="space-y-[var(--md-sys-spacing-3)]">
          <h3 className="text-[var(--md-sys-typescale-title-large-size)] px-2">今日提醒</h3>
          <GlassCard 
            variant="filled" 
            padding="md" 
            className="flex items-center gap-6 border-l-4"
            style={{ borderLeftColor: reminder.color }}
          >
            <div 
              className="w-14 h-14 rounded-full flex items-center justify-center"
              style={{ backgroundColor: `${reminder.color}20`, color: reminder.color }}
            >
              {reminder.icon}
            </div>
            <div className="flex-1">
              <p className="text-[var(--md-sys-typescale-title-large-size)] font-black">{reminder.title}</p>
              <p className="text-[var(--md-sys-typescale-body-large-size)] opacity-60">{reminder.desc}</p>
            </div>
            <Button variant="tonal" onClick={() => navigate('/chat')}>
              立即开始
            </Button>
          </GlassCard>
        </section>
      )}

      {/* 3. ENDGAME VISION */}
      <section className="space-y-[var(--md-sys-spacing-3)]">
        <h3 className="text-[var(--md-sys-typescale-title-large-size)] px-2">
          终局愿景
        </h3>
        <GlassCard variant="outlined" padding="lg" className="relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
            <Flag size={120} />
          </div>
          <div className="space-y-6 relative z-10">
            <div className="w-full">
              <h2 className="text-[var(--md-sys-typescale-headline-medium-size)] font-bold text-[var(--md-sys-color-primary)]">
                {data.vision?.title || '终局愿景'}
              </h2>
              <p className="text-[var(--md-sys-typescale-body-large-size)] mt-4 opacity-80 max-w-3xl leading-[1.8] tracking-wide text-left text-justify">
                {String(data.vision?.description || '')}
              </p>
            </div>
            <div className="w-full pt-4">
              <div className="flex justify-between items-end mb-2">
                <span className="text-[var(--md-sys-typescale-label-large-size)] font-bold opacity-40 uppercase tracking-[0.2em]">Vision Alignment</span>
                <span className="text-[var(--md-sys-typescale-display-small-size)] font-black text-[var(--md-sys-color-tertiary)] opacity-30 leading-none">{data.vision?.progress || 0}%</span>
              </div>
              <div className="h-3 bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-[var(--md-sys-color-primary)] via-[var(--md-sys-color-secondary)] to-[var(--md-sys-color-tertiary)] transition-all duration-1000"
                  style={{ width: `${data.vision?.progress || 0}%` }}
                />
              </div>
            </div>
          </div>
        </GlassCard>
      </section>

      {/* 4. GOALS & H3 GRID */}
      <div className="grid grid-cols-12 gap-[var(--md-sys-spacing-4)]">
        {/* GOALS MODULE */}
        <div className="col-span-12 lg:col-span-7 space-y-[var(--md-sys-spacing-3)]">
          <div className="flex justify-between items-center px-2">
            <h3 className="text-[var(--md-sys-typescale-title-large-size)]">核心目标</h3>
            <button className="text-[var(--md-sys-typescale-label-large-size)] text-[var(--md-sys-color-primary)] font-bold" onClick={() => navigate('/goals')}>管理目标</button>
          </div>
          <div className="space-y-[var(--md-sys-spacing-2)]">
            {data.active_goals.length > 0 ? data.active_goals.map((goal: any) => (
              <GlassCard variant="filled" padding="md" className="hover:bg-[var(--md-sys-color-surface-container-high)] transition-colors cursor-pointer group">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-[var(--md-sys-color-secondary-container)] flex items-center justify-center text-[var(--md-sys-color-on-secondary-container)]">
                    <Target size={20} />
                  </div>
                  <div className="flex-1">
                    <p className="font-bold text-[var(--md-sys-typescale-body-large-size)]">{goal.title}</p>
                    <div className="flex items-center gap-4 mt-1">
                      <div className="flex-1 h-1.5 bg-[var(--md-sys-color-surface-variant)] rounded-full overflow-hidden">
                        <div className="h-full bg-[var(--md-sys-color-secondary)]" style={{ width: `${goal.progress}%` }} />
                      </div>
                      <span className="text-xs opacity-60 font-mono">{goal.progress}%</span>
                    </div>
                  </div>
                  <ChevronRight size={20} className="opacity-20 group-hover:opacity-100 transition-opacity" />
                </div>
              </GlassCard>
            )) : (
              <p className="p-8 text-center opacity-40 italic bg-[var(--md-sys-color-surface-container-low)] rounded-[var(--md-sys-shape-corner-large)]">暂无活跃目标，建议去“目标”页面建立你的第一个坐标</p>
            )}
          </div>
        </div>

        {/* H3 ENERGY - INTERACTIVE */}
        <div className="col-span-12 lg:col-span-5 space-y-[var(--md-sys-spacing-3)]">
          <div className="flex justify-between items-center px-2">
            <h3 className="text-[var(--md-sys-typescale-title-large-size)]">H3 能量状态</h3>
            <span className="text-2xl font-black text-[var(--md-sys-color-primary)]">{h3Total}%</span>
          </div>
          <GlassCard variant="filled" padding="lg" className="space-y-6">
            <div className="grid grid-cols-1 gap-6">
              {h3Dimensions.map((dim) => (
                <div key={dim.key} className="space-y-3">
                  <div className="flex justify-between text-[var(--md-sys-typescale-label-large-size)]">
                    <span className="flex items-center gap-2">
                      <span className="text-xl">{dim.icon}</span>
                      <span className="font-bold">{dim.label}</span>
                    </span>
                    <span className="font-mono font-bold" style={{ color: dim.color }}>{localScores[dim.key] || 0}%</span>
                  </div>
                  <Slider
                    value={[localScores[dim.key] || 0]}
                    max={100}
                    step={5}
                    onValueChange={(val: number[]) => handleScoreChange(dim.key, val)}
                  />
                </div>
              ))}
            </div>
            <Button 
              className="w-full h-12" 
              icon={<Activity size={18} />}
              onClick={handleCalibrate}
              loading={isCalibrating}
            >
              立即校准
            </Button>
          </GlassCard>
        </div>
      </div>

      {/* 5. RECENT ACTIVITIES - System Logs */}
      <section className="space-y-[var(--md-sys-spacing-3)]">
        <div className="flex justify-between items-center px-2">
          <h3 className="text-[var(--md-sys-typescale-title-large-size)]">系统动态</h3>
          <button className="text-[var(--md-sys-typescale-label-large-size)] text-[var(--md-sys-color-primary)] font-bold">查看全部</button>
        </div>
        <div className="space-y-[var(--md-sys-spacing-1)]">
          {data.recent_activities.length > 0 ? data.recent_activities.map((log: any) => (
            <div key={log.id} className="flex items-center gap-4 p-4 rounded-[var(--md-sys-shape-corner-large)] hover:bg-[var(--md-sys-color-surface-container)] transition-colors group">
              <div className="w-10 h-10 rounded-full bg-[var(--md-sys-color-surface-container-highest)] flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] group-hover:bg-[var(--md-sys-color-primary-container)] group-hover:text-[var(--md-sys-color-on-primary-container)] transition-colors">
                {log.type === 'chat' ? <MessageSquare size={18} /> : log.type === 'calibration' ? <Zap size={18} /> : <Activity size={18} />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[var(--md-sys-typescale-body-large-size)] font-bold truncate">{log.title}</p>
                <p className="text-[var(--md-sys-typescale-body-medium-size)] opacity-60 truncate">{log.description}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-[var(--md-sys-typescale-label-small-size)] opacity-40 font-mono">{formatTime(log.created_at)}</p>
              </div>
            </div>
          )) : (
            <p className="p-8 text-center opacity-40 italic">暂无系统操作记录</p>
          )}
        </div>
      </section>
    </div>
  );
}
