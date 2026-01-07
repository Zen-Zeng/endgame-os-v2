/**
 * 仪表盘页面
 * 按照原型图 Layout 2 设计
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  MessageSquare,
  Target,
  TrendingUp,
  TrendingDown,
  Clock,
  Zap,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import { useAuthStore } from '../stores/useAuthStore';
import { useH3Store } from '../stores/useH3Store';
import { useOnboardingStore } from '../stores/useOnboardingStore';
import { api } from '../lib/api';

// H3 维度配置
const h3Dimensions = [
  { key: 'mind', label: '心智', color: 'var(--color-h3-mind)' },
  { key: 'body', label: '身体', color: 'var(--color-h3-body)' },
  { key: 'spirit', label: '精神', color: 'var(--color-h3-spirit)' },
  { key: 'vocation', label: '志业', color: 'var(--color-h3-vocation)' },
] as const;

interface DashboardStats {
  totalConversations: number;
  streakDays: number;
  goalsProgress: number;
  todayMessages: number;
}

interface ActivityItem {
  id: string;
  type: 'chat' | 'calibration' | 'goal' | 'memory';
  title: string;
  time: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { scores: storeScores, fetchCurrentState, isLoading: h3Loading } = useH3Store();
  const { personaConfig: onboardingPersonaConfig, h3InitialState } = useOnboardingStore();
  
  // 优先使用 H3Store 的数据，如果为空则使用 onboarding 的初始数据
  const defaultScores = { mind: 0, body: 0, spirit: 0, vocation: 0 };
  const onboardingScores = h3InitialState ? {
    mind: h3InitialState.mind,
    body: h3InitialState.body,
    spirit: h3InitialState.spirit,
    vocation: h3InitialState.vocation,
  } : defaultScores;
  
  // 如果 storeScores 全为 0，使用 onboarding 数据
  const hasStoreData = storeScores && (storeScores.mind > 0 || storeScores.body > 0 || storeScores.spirit > 0 || storeScores.vocation > 0);
  const scores = hasStoreData ? storeScores : (onboardingScores.mind > 0 ? onboardingScores : defaultScores);
  
  const [greeting, setGreeting] = useState('');
  const [stats, setStats] = useState<DashboardStats>({
    totalConversations: 0,
    streakDays: 0,
    goalsProgress: 0,
    todayMessages: 0,
  });
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [personaName, setPersonaName] = useState<string>('The Architect');
  const [userVision, setUserVision] = useState<string>('');

  // 设置问候语
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('早安');
    else if (hour < 18) setGreeting('下午好');
    else setGreeting('晚上好');
  }, []);

  // 获取 H3 状态
  useEffect(() => {
    fetchCurrentState();
  }, [fetchCurrentState]);

  // 获取用户配置数据（数字人格、愿景等）
  useEffect(() => {
    const fetchUserConfig = async () => {
      try {
        // 获取数字人格配置
        const personaData = await api.get('/persona/current').catch(() => null);
        if (personaData?.name) {
          setPersonaName(personaData.name);
        } else if (onboardingPersonaConfig?.aiName) {
          setPersonaName(onboardingPersonaConfig.aiName);
        }

        // 获取用户愿景
        const userData = await api.get('/auth/me').catch(() => null);
        if (userData?.vision?.description) {
          setUserVision(userData.vision.description);
        } else if (onboardingPersonaConfig?.vision) {
          setUserVision(onboardingPersonaConfig.vision);
        }
      } catch (error) {
        console.error('获取用户配置失败:', error);
        // 使用 onboarding 数据作为后备
        if (onboardingPersonaConfig) {
          setPersonaName(onboardingPersonaConfig.aiName || 'The Architect');
          setUserVision(onboardingPersonaConfig.vision || '');
        }
      }
    };

    fetchUserConfig();
  }, [onboardingPersonaConfig]);

  // 获取仪表盘统计数据
  useEffect(() => {
    const fetchStats = async () => {
      setIsLoadingStats(true);
      try {
        const response = await api.get<{ stats: DashboardStats; activities: ActivityItem[] }>('/dashboard/stats');
        // 确保不会设置 undefined
        if (response?.stats) {
          setStats(response.stats);
        }
        if (response?.activities) {
          setActivities(response.activities);
        }
      } catch (error) {
        console.error('获取仪表盘数据失败:', error);
        // 保持默认状态，不做任何更改
      } finally {
        setIsLoadingStats(false);
      }
    };

    fetchStats();
  }, []);

  // 计算 H3 总分
  const h3Total = Math.round(
    (scores.mind + scores.body + scores.spirit + scores.vocation) / 4
  );

  // 根据分数判断趋势（简化逻辑，后续可从后端获取）
  const h3Trend = h3Total >= 60 ? 'up' : 'down';

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays === 1) return '昨天';
    return `${diffDays}天前`;
  };

  // 获取用户显示名称（优先使用后端数据，然后是 onboarding 数据）
  const displayName = user?.name || onboardingPersonaConfig?.nickname || '用户';

  return (
    <div className="dashboard-page">
      {/* 页面标题 */}
      <header className="page-header animate-fade-in-down">
        <h1 className="page-title">
          {greeting}，{displayName}
        </h1>
        <p className="page-subtitle">
          {(stats?.streakDays ?? 0) > 0 
            ? `今天是你连续活跃的第 ${stats?.streakDays ?? 0} 天 🔥`
            : '开始你的第一天，建立能量追踪习惯 ✨'
          }
        </p>
      </header>

      {/* 主要内容区域 */}
      <div className="dashboard-grid">
        {/* H3 能量概览 - 大卡片 */}
        <div className="col-span-12 lg:col-span-8">
          <GlassCard className="animate-fade-in-up" hover>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-display text-xl font-semibold text-[var(--color-text-primary)]">
                  H3 能量状态
                </h2>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  今日综合能量
                </p>
              </div>
              <div className="flex items-center gap-2">
                {h3Loading ? (
                  <Loader2 className="animate-spin text-[var(--color-primary)]" size={24} />
                ) : (
                  <>
                    <span className="text-4xl font-bold text-[var(--color-primary)]">
                      {h3Total}%
                    </span>
                    {h3Trend === 'up' ? (
                      <TrendingUp className="text-[var(--color-success)]" size={24} />
                    ) : (
                      <TrendingDown className="text-[var(--color-error)]" size={24} />
                    )}
                  </>
                )}
              </div>
            </div>

            {/* 四维能量条 */}
            <div className="grid grid-cols-2 gap-6">
              {h3Dimensions.map((dim) => {
                const value = scores[dim.key];
                return (
                  <div key={dim.key}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-[var(--color-text-secondary)]">
                        {dim.label}
                      </span>
                      <span className="text-sm font-medium text-[var(--color-text-primary)]">
                        {value}%
                      </span>
                    </div>
                    <div className="h-3 bg-[var(--color-bg-darker)] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-1000"
                        style={{
                          width: `${value}%`,
                          backgroundColor: dim.color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 快捷操作 */}
            <div className="mt-6 pt-6 border-t border-[var(--color-border-light)] flex gap-4">
              <button 
                className="btn btn-primary flex-1"
                onClick={() => navigate('/calibration')}
              >
                <Activity size={18} />
                开始校准
              </button>
              <button 
                className="btn btn-secondary flex-1"
                onClick={() => navigate('/chat')}
              >
                <MessageSquare size={18} />
                与 AI 对话
              </button>
            </div>
          </GlassCard>
        </div>

        {/* 统计卡片 */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* 对话统计 */}
          <GlassCard className="animate-fade-in-up delay-100" hover>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[var(--color-primary-alpha-20)] flex items-center justify-center">
                <MessageSquare className="text-[var(--color-primary)]" size={24} />
              </div>
              <div>
                {isLoadingStats ? (
                  <Loader2 className="animate-spin text-[var(--color-primary)]" size={20} />
                ) : (
                  <>
                    <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                      {stats?.totalConversations ?? 0}
                    </p>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      总对话数
                    </p>
                  </>
                )}
              </div>
            </div>
          </GlassCard>

          {/* 目标进度 */}
          <GlassCard className="animate-fade-in-up delay-200" hover>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[var(--color-success)]/20 flex items-center justify-center">
                <Target className="text-[var(--color-success)]" size={24} />
              </div>
              <div className="flex-1">
                {isLoadingStats ? (
                  <Loader2 className="animate-spin text-[var(--color-primary)]" size={20} />
                ) : (
                  <>
                    <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                      {stats?.goalsProgress ?? 0}%
                    </p>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      目标完成度
                    </p>
                  </>
                )}
              </div>
            </div>
            <div className="mt-4 h-2 bg-[var(--color-bg-darker)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--color-success)] rounded-full transition-all duration-1000"
                style={{ width: `${stats?.goalsProgress ?? 0}%` }}
              />
            </div>
          </GlassCard>

          {/* 今日活跃 */}
          <GlassCard className="animate-fade-in-up delay-300" hover>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[var(--color-warning)]/20 flex items-center justify-center">
                <Zap className="text-[var(--color-warning)]" size={24} />
              </div>
              <div>
                {isLoadingStats ? (
                  <Loader2 className="animate-spin text-[var(--color-primary)]" size={20} />
                ) : (
                  <>
                    <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                      {stats?.todayMessages ?? 0}
                    </p>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      今日消息
                    </p>
                  </>
                )}
              </div>
            </div>
          </GlassCard>
        </div>

        {/* 最近活动 */}
        <div className="col-span-12 lg:col-span-6">
          <GlassCard className="animate-fade-in-up delay-400">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-lg font-semibold text-[var(--color-text-primary)]">
                最近活动
              </h2>
              <button 
                className="text-[var(--color-primary)] text-sm hover:underline flex items-center gap-1"
                onClick={() => navigate('/archives')}
              >
                查看全部 <ChevronRight size={16} />
              </button>
            </div>

            <div className="space-y-4">
              {activities.length === 0 ? (
                <div className="text-center py-8 text-[var(--color-text-muted)]">
                  <p>还没有活动记录</p>
                  <p className="text-sm mt-1">开始与 AI 对话或进行 H3 校准</p>
                </div>
              ) : (
                activities.slice(0, 5).map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center gap-4 p-3 rounded-xl hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
                  >
                    <div className="w-10 h-10 rounded-lg bg-[var(--color-primary-alpha-20)] flex items-center justify-center">
                      {activity.type === 'chat' && (
                        <MessageSquare size={18} className="text-[var(--color-primary)]" />
                      )}
                      {activity.type === 'calibration' && (
                        <Activity size={18} className="text-[var(--color-primary)]" />
                      )}
                      {activity.type === 'goal' && (
                        <Target size={18} className="text-[var(--color-primary)]" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[var(--color-text-primary)]">
                        {activity.title}
                      </p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {formatTime(activity.time)}
                      </p>
                    </div>
                    <ChevronRight size={16} className="text-[var(--color-text-muted)]" />
                  </div>
                ))
              )}
            </div>
          </GlassCard>
        </div>

        {/* 今日提醒 */}
        <div className="col-span-12 lg:col-span-6">
          <GlassCard className="animate-fade-in-up delay-500">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-lg font-semibold text-[var(--color-text-primary)]">
                今日提醒
              </h2>
              <span className="badge badge-primary">
                {h3Total < 50 ? '3 项' : '2 项'}
              </span>
            </div>

            <div className="space-y-3">
              <div 
                className="flex items-start gap-3 p-3 rounded-xl bg-[var(--color-primary-alpha-20)] border border-[var(--color-primary-alpha-40)] cursor-pointer"
                onClick={() => navigate('/calibration')}
              >
                <Clock size={18} className="text-[var(--color-primary)] mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">
                    晨间 H3 校准
                  </p>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    保持每日校准习惯
                  </p>
                </div>
              </div>

              {h3Total < 50 && (
                <div 
                  className="flex items-start gap-3 p-3 rounded-xl bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 cursor-pointer"
                  onClick={() => navigate('/chat')}
                >
                  <Zap size={18} className="text-[var(--color-warning)] mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">
                      能量偏低，建议对话
                    </p>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      与 AI 聊聊你的状态
                    </p>
                  </div>
                </div>
              )}

              <div 
                className="flex items-start gap-3 p-3 rounded-xl hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
                onClick={() => navigate('/chat')}
              >
                <MessageSquare size={18} className="text-[var(--color-text-muted)] mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">
                    与 {personaName} 进行对话
                  </p>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    保持终局聚焦
                  </p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
