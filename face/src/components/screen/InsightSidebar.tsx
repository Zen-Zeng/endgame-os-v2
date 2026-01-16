import { useMemo } from 'react';
import { 
  Target, 
  Sparkles, 
  Calendar,
  Coffee,
  Moon,
  PieChart,
  Flag,
  ArrowUpRight
} from 'lucide-react';
import clsx from 'clsx';

interface InsightSidebarProps {
  aiSummary: string;
  vision: {
    title: string;
    description: string;
    progress: number;
  };
  userName?: string;
  className?: string;
  mode?: 'full' | 'pulse-only' | 'nudges-only' | 'vision-only';
}

export default function InsightSidebar({ aiSummary, vision, userName = '岳', className, mode = 'full' }: InsightSidebarProps) {
  // 生成数字分身问候语
  const fullGreeting = useMemo(() => {
    const now = new Date();
    const hour = now.getHours();
    
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
      '心智引擎已就绪，准备开始今天的进化吗？'
    ];
    const randomFutureMsg = futureMessages[Math.floor(Math.random() * futureMessages.length)];
    
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const dateStr = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${days[now.getDay()]}`;

    return { 
      greeting: `${userName}，${timeGreeting}。`, 
      date: dateStr,
      sub: randomFutureMsg 
    };
  }, [userName]);

  // 今日提醒逻辑
  const reminder = useMemo(() => {
    const now = new Date();
    const hour = now.getHours();
    const day = now.getDay();
    const isLastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate() === now.getDate();

    if (isLastDayOfMonth && hour >= 18) {
      return {
        title: '月度系统审计',
        desc: '本月终局对齐度评估，重新校准长期航线',
        icon: <PieChart size={24} />,
        color: 'var(--md-sys-color-tertiary)'
      };
    }
    if (day === 0 && hour >= 18) {
      return {
        title: '周中枢盘点',
        desc: '回顾本周进展，规划下周核心突破点',
        icon: <Calendar size={24} />,
        color: 'var(--md-sys-color-secondary)'
      };
    }
    if (hour >= 17) {
      return {
        title: '日终复盘',
        desc: '记录今日洞察，清理认知缓存',
        icon: <Moon size={24} />,
        color: 'var(--md-sys-color-primary)'
      };
    }
    if (hour >= 8) {
      return {
        title: '日启动协议',
        desc: '同步终局愿景，锁定今日 Critical Task',
        icon: <Coffee size={24} />,
        color: 'var(--md-sys-color-primary)'
      };
    }
    return null;
  }, []);

  return (
    <div className={clsx(
      "flex flex-col gap-6",
      mode === 'full' && "p-6 bg-[var(--md-sys-color-surface-container-low)] border-l border-[var(--md-sys-color-outline-variant)] h-full overflow-y-auto custom-scrollbar",
      className
    )}>
      {/* 1. AI 摘要 & 问候 (The Pulse) - 合并模式 */}
      {(mode === 'full' || mode === 'pulse-only') && (
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-[var(--md-sys-color-primary)] font-black text-xs uppercase tracking-widest">
              <Sparkles size={16} />
              系统脉搏 / The Pulse
            </div>
            <div className="text-[10px] font-bold text-[var(--md-sys-color-outline)] uppercase tracking-tighter opacity-60">
              {fullGreeting.date}
            </div>
          </div>

          <div className="space-y-4">
            <div className="space-y-1">
              <h2 className="text-2xl font-black text-[var(--md-sys-color-on-surface)] leading-tight">
                {fullGreeting.greeting}
              </h2>
              <p className="text-xs text-[var(--md-sys-color-primary)] font-bold italic opacity-90">
                「{fullGreeting.sub}」
              </p>
            </div>

            <div className="relative p-5 bg-[var(--md-sys-color-surface-container-highest)] rounded-3xl border border-[var(--md-sys-color-outline-variant)] shadow-sm overflow-hidden group">
              <div className="relative z-10 space-y-2">
                <span className="text-[10px] font-black uppercase text-[var(--md-sys-color-outline)] tracking-widest opacity-50">AI 核心摘要 / Summary</span>
                <p className="text-sm text-[var(--md-sys-color-on-surface-variant)] leading-relaxed font-medium">
                  {aiSummary}
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 2. 今日提醒 (Daily Nudges) - 独立模块 */}
      {(mode === 'full' || mode === 'nudges-only') && reminder && (
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-[var(--md-sys-color-secondary)] font-black text-xs uppercase tracking-widest">
            <Calendar size={16} />
            今日提醒 / Nudges
          </div>
          <div 
            className="group relative p-5 rounded-[var(--md-sys-shape-corner-extra-large)] border transition-all hover:shadow-md overflow-hidden bg-[var(--md-sys-color-surface-container-high)]"
            style={{ 
              borderColor: `${reminder.color}30`
            }}
          >
            <div className="flex items-start gap-4">
              <div 
                className="p-3 rounded-xl text-white shadow-lg shadow-black/5"
                style={{ backgroundColor: reminder.color }}
              >
                {reminder.icon}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-black text-sm uppercase tracking-tight" style={{ color: reminder.color }}>{reminder.title}</h3>
                  <span className="w-1 h-1 rounded-full bg-[var(--md-sys-color-outline-variant)]" />
                  <span className="text-[10px] font-bold text-[var(--md-sys-color-outline)] opacity-60">REQUIRED ACTION</span>
                </div>
                <p className="text-sm text-[var(--md-sys-color-on-surface-variant)] leading-relaxed font-bold">{reminder.desc}</p>
              </div>
              <ArrowUpRight size={18} className="text-[var(--md-sys-color-outline)] opacity-0 group-hover:opacity-100 transition-all transform group-hover:translate-x-1 group-hover:-translate-y-1" />
            </div>
            
            {/* 装饰性背景 */}
            <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
               {typeof reminder.icon === 'object' ? <reminder.icon.type {...reminder.icon.props} size={80} /> : null}
            </div>
          </div>
        </section>
      )}

      {/* 3. 终局愿景 (Ultimate Vision) */}
      {(mode === 'full' || mode === 'vision-only') && (
        <section className={clsx("space-y-4", mode === 'full' && "mt-auto pt-6")}>
          <div className="flex items-center gap-2 text-[var(--md-sys-color-tertiary)] font-black text-xs uppercase tracking-widest">
            <Target size={16} />
            终局愿景 / Vision
          </div>
          <div className="p-5 bg-[var(--md-sys-color-surface-container-high)] rounded-[var(--md-sys-shape-corner-extra-large)] border-2 border-dashed border-[var(--md-sys-color-tertiary)]/30 relative overflow-hidden group">
            <div className="relative z-10 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-black text-lg text-[var(--md-sys-color-on-surface)]">{vision.title || '终局愿景'}</h3>
                <Flag size={20} className="text-[var(--md-sys-color-tertiary)]" />
              </div>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed line-clamp-4 italic">
                {vision.description || '尚未定义终局愿景，请前往对话或目标管理进行设定。'}
              </p>
              {vision.progress > 0 && (
                <div className="space-y-1.5 pt-2">
                  <div className="flex justify-between text-[10px] font-black uppercase">
                    <span>进化进度</span>
                    <span>{vision.progress}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-[var(--md-sys-color-surface-variant)] rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-[var(--md-sys-color-tertiary)] transition-all duration-1000"
                      style={{ width: `${vision.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            {/* Background Decoration */}
            <div className="absolute -bottom-4 -right-4 text-[var(--md-sys-color-tertiary)] opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
              <Target size={120} />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
