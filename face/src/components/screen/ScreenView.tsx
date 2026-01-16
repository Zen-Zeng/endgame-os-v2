import { useEffect, useState } from 'react';
import { Activity, Share2, Database } from 'lucide-react';
import VitalityHeader from './VitalityHeader';
import InsightSidebar from './InsightSidebar';
import MemoryGraph from './MemoryGraph';
import MemoryArchive from './MemoryArchive';
import GoalsSection from './GoalsSection';
import { api } from '../../lib/api';
import { useAuthStore } from '../../stores/useAuthStore';
import { useH3Store } from '../../stores/useH3Store';

/**
 * 一屏 (Screen View)
 * 整合所有非对话功能：数据看板、记忆图谱、档案库、训练中心
 */
export default function ScreenView() {
  const { user } = useAuthStore();
  const { fetchCurrentState } = useH3Store();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>({
    stats: {
      total_conversations: 0,
      streak_days: 0,
      energy_points: 0
    },
    ai_summary: '正在同步系统实时状态...',
    vision: {
      title: '终局愿景',
      description: '',
      progress: 0
    }
  });

  const fetchData = async () => {
    try {
      const response = await api.get<any>('/dashboard/overview');
      if (response) {
        setData(response);
      }
    } catch (e) {
      console.error('Fetch screen data error', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchCurrentState();
  }, [fetchCurrentState]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--md-sys-color-primary)]"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[var(--md-sys-color-surface-container-lowest)] overflow-y-auto custom-scrollbar relative">
      {/* 吸顶状态栏 / Sticky Status Bar */}
      <div className="sticky top-0 z-30 bg-[var(--md-sys-color-surface-container-lowest)]/80 backdrop-blur-md border-b border-[var(--md-sys-color-outline-variant)] px-6 py-3 shadow-sm">
        <VitalityHeader stats={data.stats} className="!p-0 !bg-transparent !border-none" />
      </div>

      {/* 1. 系统脉搏 (AI 摘要 & 问候) */}
      <section className="p-6 pb-0">
        <InsightSidebar 
          mode="pulse-only"
          aiSummary={data.ai_summary} 
          vision={data.vision} 
          userName={user?.name}
        />
      </section>

      {/* 2. 今日提醒 (Nudges) */}
      <section className="p-6 pb-0">
        <InsightSidebar 
          mode="nudges-only"
          aiSummary={data.ai_summary} 
          vision={data.vision} 
          userName={user?.name}
        />
      </section>

      {/* 3. 终局愿景 */}
      <section className="p-6 pb-0">
        <InsightSidebar 
          mode="vision-only"
          aiSummary={data.ai_summary} 
          vision={data.vision} 
          userName={user?.name}
        />
      </section>

      {/* 4. 目标中枢 (GoalsSection) */}
      <section className="p-6 pb-0 space-y-4">
        <div className="flex items-center gap-2 text-[var(--md-sys-color-primary)] font-black text-xs uppercase tracking-widest px-1">
          <Activity size={16} />
          目标中枢 / Core Goals
        </div>
        <GoalsSection />
      </section>

      {/* 5. 记忆图谱 */}
      <section className="p-6 pb-0 space-y-4">
        <div className="flex items-center gap-2 text-[var(--md-sys-color-primary)] font-black text-xs uppercase tracking-widest px-1">
          <Share2 size={16} />
          记忆图谱 / Knowledge Graph
        </div>
        <div className="h-[500px] flex-shrink-0">
          <MemoryGraph className="h-full rounded-3xl border border-[var(--md-sys-color-outline-variant)] shadow-sm overflow-hidden" />
        </div>
      </section>

      {/* 6. 记忆档案库 (已整合注入、流水线、贡献链展示) */}
      <section className="p-6 pb-12 space-y-4">
        <div className="flex items-center gap-2 text-[var(--md-sys-color-primary)] font-black text-xs uppercase tracking-widest px-1">
          <Database size={16} />
          战略情报中心 / Intelligence Center
        </div>
        <div className="h-[800px] flex-shrink-0">
          <MemoryArchive 
            onRefreshGraph={fetchCurrentState}
            className="h-full" 
          />
        </div>
      </section>
    </div>
  );
}
