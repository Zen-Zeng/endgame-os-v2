/**
 * Endgame OS v2 - H3 Calibration Page
 * Strictly following M3 Grid, Typography and Component specs
 */
import { useState, useEffect } from 'react';
import { Save, TrendingUp, Minus, Plus, History, Loader2, Activity, Info } from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import { useH3Store, type H3Scores } from '../stores/useH3Store';

// H3 维度配置 - 与 Dashboard 保持同步
const h3Dimensions: Array<{
  key: keyof H3Scores;
  label: string;
  description: string;
  color: string;
  icon: string;
}> = [
  {
    key: 'mind',
    label: '心智',
    description: '专注力、创造力、学习能力',
    color: 'var(--md-sys-color-primary)',
    icon: '🧠',
  },
  {
    key: 'body',
    label: '身体',
    description: '精力、健康状态、睡眠质量',
    color: '#aaddbf',
    icon: '💪',
  },
  {
    key: 'spirit',
    label: '精神',
    description: '动力、意义感、情绪状态',
    color: '#ffb4a9',
    icon: '✨',
  },
  {
    key: 'vocation',
    label: '志业',
    description: '事业进展、目标推进、成就感',
    color: '#a8c7fa',
    icon: '🎯',
  },
];

export default function CalibrationPage() {
  const { scores, updateScores, fetchCurrentState, fetchHistory, history } = useH3Store();
  const [values, setValues] = useState({
    mind: 50,
    body: 50,
    spirit: 50,
    vocation: 50,
  });
  const [moodNote, setMoodNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // 初始化时同步全局 Store 状态
  useEffect(() => {
    fetchCurrentState();
    fetchHistory();
  }, []);

  // 当全局 scores 变化时更新本地 values (仅在非保存状态下)
  useEffect(() => {
    if (!isSaving) {
      setValues(scores);
    }
  }, [scores, isSaving]);

  const total = Math.round(
    (values.mind + values.body + values.spirit + values.vocation) / 4
  );

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateScores(values, moodNote, 'manual');
      await fetchHistory(); // 保存成功后刷新历史记录
      setMoodNote(''); // 清空笔记
    } catch (error) {
      console.error('保存失败:', error);
    } finally {
      setIsSaving(false);
    }
  };

  // 模拟历史数据
  const historyData = [
    { date: '今天', mind: values.mind, body: values.body, spirit: values.spirit, vocation: values.vocation },
    { date: '昨天', mind: 65, body: 55, spirit: 70, vocation: 60 },
    { date: '前天', mind: 60, body: 58, spirit: 65, vocation: 55 },
  ];

  return (
    <div className="page-container space-y-[var(--md-sys-spacing-5)]">
      {/* 1. HEADER SECTION */}
      <header className="py-[var(--md-sys-spacing-3)]">
        <div className="flex items-center gap-3 mb-2">
           <Activity className="text-[var(--md-sys-color-primary)]" size={32} />
           <h1 className="text-[var(--md-sys-typescale-display-medium-size)] font-bold text-[var(--md-sys-color-on-background)] tracking-tight">
             H3 能量校准
           </h1>
        </div>
        <p className="text-[var(--md-sys-typescale-body-large-size)] text-[var(--md-sys-color-on-surface-variant)] opacity-70">
          通过多维度自我观测，同步你当下的真实能量频率
        </p>
      </header>

      <div className="grid grid-cols-12 gap-[var(--md-sys-spacing-4)]">
        {/* 2. MAIN CALIBRATION AREA (L:7) */}
        <div className="col-span-12 lg:col-span-7">
          <GlassCard variant="elevated" padding="lg" className="relative overflow-hidden">
            {/* 动态背景装饰 */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--md-sys-color-primary)] opacity-[0.03] blur-[100px] -mr-32 -mt-32" />
            
            {/* 总分核心显示 */}
            <div className="text-center mb-[var(--md-sys-spacing-8)] py-6">
                <div className="text-[140px] font-black text-[var(--md-sys-color-primary)] leading-none tracking-tighter transition-all duration-700">
                  {total}
                </div>
                <div className="flex items-center justify-center gap-[var(--md-sys-spacing-4)] mt-4">
                  <div className="w-12 h-px bg-gradient-to-r from-transparent to-[var(--md-sys-color-outline-variant)]" />
                  <p className="text-[var(--md-sys-typescale-label-large-size)] font-black uppercase tracking-[0.4em] text-[var(--md-sys-color-on-surface-variant)] opacity-40">
                    Energy Index
                  </p>
                  <div className="w-12 h-px bg-gradient-to-l from-transparent to-[var(--md-sys-color-outline-variant)]" />
                </div>
            </div>

            {/* 维度调节器列表 */}
            <div className="space-y-[var(--md-sys-spacing-6)]">
              {h3Dimensions.map((dim) => (
                <div key={dim.key} className="group">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-[var(--md-sys-shape-corner-medium)] bg-[var(--md-sys-color-surface-container-high)] flex items-center justify-center text-2xl shadow-sm group-hover:scale-110 transition-transform">
                        {dim.icon}
                      </div>
                      <div>
                        <h3 className="text-[var(--md-sys-typescale-title-medium-size)] font-bold text-[var(--md-sys-color-on-surface)]">
                          {dim.label}
                        </h3>
                        <p className="text-[var(--md-sys-typescale-label-medium-size)] text-[var(--md-sys-color-on-surface-variant)] opacity-60">
                          {dim.description}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[var(--md-sys-typescale-headline-small-size)] font-black text-[var(--md-sys-color-primary)]">
                        {values[dim.key]}%
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => setValues(v => ({ ...v, [dim.key]: Math.max(0, v[dim.key] - 5) }))}
                      className="w-12 h-12 rounded-full flex items-center justify-center bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-primary)] hover:text-[var(--md-sys-color-on-primary)] transition-all active:scale-90 shadow-sm"
                    >
                      <Minus size={20} />
                    </button>
                    
                    <div className="flex-1 h-3 bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden relative shadow-inner">
                      <div
                        className="absolute inset-y-0 left-0 transition-all duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
                        style={{
                          width: `${values[dim.key]}%`,
                          backgroundColor: dim.color,
                        }}
                      />
                    </div>

                    <button
                      onClick={() => setValues(v => ({ ...v, [dim.key]: Math.min(100, v[dim.key] + 5) }))}
                      className="w-12 h-12 rounded-full flex items-center justify-center bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-primary)] hover:text-[var(--md-sys-color-on-primary)] transition-all active:scale-90 shadow-sm"
                    >
                      <Plus size={20} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* 备注与提交 */}
            <div className="mt-[var(--md-sys-spacing-8)] pt-8 border-t border-[var(--md-sys-color-outline-variant)] space-y-4">
              <div className="relative">
                <textarea
                  placeholder="记录当下的身体感觉、心智杂念或灵感发现..."
                  value={moodNote}
                  onChange={(e) => setMoodNote(e.target.value)}
                  className="w-full h-32 bg-[var(--md-sys-color-surface-container-low)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-extra-large)] p-4 text-[var(--md-sys-typescale-body-large-size)] focus:ring-2 focus:ring-[var(--md-sys-color-primary)] focus:border-transparent transition-all outline-none resize-none placeholder:opacity-30"
                />
              </div>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="w-full py-5 bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] rounded-[var(--md-sys-shape-corner-full)] font-bold text-[var(--md-sys-typescale-title-medium-size)] flex items-center justify-center gap-3 hover:shadow-xl hover:translate-y-[-2px] transition-all active:scale-[0.98] disabled:opacity-50 shadow-lg shadow-[var(--md-sys-color-primary)]/20"
              >
                {isSaving ? <Loader2 className="animate-spin" /> : <Save size={20} />}
                {isSaving ? '正在同步至 H3 核心...' : '确认当前状态并保存'}
              </button>
            </div>
          </GlassCard>
        </div>

        {/* 3. SIDE INFO AREA (L:5) */}
        <div className="col-span-12 lg:col-span-5 space-y-[var(--md-sys-spacing-4)]">
          {/* 能量趋势 */}
          <GlassCard variant="filled" padding="md" className="border border-[var(--md-sys-color-outline-variant)]">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <TrendingUp size={20} className="text-[var(--md-sys-color-primary)]" />
                <h3 className="text-[var(--md-sys-typescale-title-medium-size)] font-bold">能量趋势分析</h3>
              </div>
              <button className="text-[var(--md-sys-color-primary)] hover:underline text-sm font-bold">查看详情</button>
            </div>
            
            <div className="space-y-3">
              {historyData.map((data, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-[var(--md-sys-color-surface-container-high)] rounded-[var(--md-sys-shape-corner-large)] group hover:bg-[var(--md-sys-color-surface-container-highest)] transition-colors">
                  <div className="flex flex-col">
                    <span className="text-[var(--md-sys-typescale-body-medium-size)] font-bold">{data.date}</span>
                    <span className="text-[var(--md-sys-typescale-label-small-size)] opacity-40">校准完成</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex -space-x-2">
                      {[data.mind, data.body, data.spirit, data.vocation].map((v, i) => (
                        <div
                          key={i}
                          className="w-6 h-6 rounded-full border-2 border-[var(--md-sys-color-surface-container-high)] shadow-sm group-hover:border-[var(--md-sys-color-surface-container-highest)] transition-colors"
                          style={{ backgroundColor: h3Dimensions[i].color, opacity: 0.3 + (v / 100) * 0.7 }}
                          title={h3Dimensions[i].label}
                        />
                      ))}
                    </div>
                    <div className="w-12 text-right">
                       <span className="text-[var(--md-sys-typescale-title-medium-size)] font-black text-[var(--md-sys-color-primary)]">
                         {Math.round((data.mind + data.body + data.spirit + data.vocation) / 4)}
                       </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* 系统建议 */}
          <GlassCard variant="outlined" padding="lg" className="bg-[var(--md-sys-color-secondary-container)]/30 border-none">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] rounded-2xl shadow-sm">
                <Info size={24} />
              </div>
              <div>
                <h4 className="text-[var(--md-sys-typescale-title-medium-size)] font-bold text-[var(--md-sys-color-on-secondary-container)] mb-2">
                  关于校准频率
                </h4>
                <p className="text-[var(--md-sys-typescale-body-medium-size)] text-[var(--md-sys-color-on-secondary-container)] opacity-80 leading-relaxed">
                  建议每天在**早晨醒来**或**完成深度工作**后进行校准。长期且诚实的记录将帮助 Endgame AI 为你生成更精准的志业路径建议。
                </p>
              </div>
            </div>
          </GlassCard>

          {/* 历史记录按钮 */}
          <button className="w-full py-4 border-2 border-dashed border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-large)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-low)] hover:border-[var(--md-sys-color-primary)] hover:text-[var(--md-sys-color-primary)] transition-all flex items-center justify-center gap-2 font-bold opacity-60 hover:opacity-100">
            <History size={18} /> 查看完整校准历史
          </button>
        </div>
      </div>
    </div>
  );
}
