/**
 * H3 校准页面
 * 按照原型图 Layout 6-8 设计
 */
import { useState } from 'react';
import { Save, TrendingUp, TrendingDown, Minus, History } from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import clsx from 'clsx';

// H3 维度配置
const h3Dimensions = [
  {
    key: 'mind',
    label: '心智',
    description: '专注力、创造力、学习能力',
    color: 'var(--color-h3-mind)',
    icon: '🧠',
  },
  {
    key: 'body',
    label: '身体',
    description: '精力、健康状态、睡眠质量',
    color: 'var(--color-h3-body)',
    icon: '💪',
  },
  {
    key: 'spirit',
    label: '精神',
    description: '动力、意义感、情绪状态',
    color: 'var(--color-h3-spirit)',
    icon: '✨',
  },
  {
    key: 'vocation',
    label: '志业',
    description: '事业进展、目标推进、成就感',
    color: 'var(--color-h3-vocation)',
    icon: '🎯',
  },
];

export default function CalibrationPage() {
  const [values, setValues] = useState({
    mind: 50,
    body: 50,
    spirit: 50,
    vocation: 50,
  });
  const [moodNote, setMoodNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const total = Math.round(
    (values.mind + values.body + values.spirit + values.vocation) / 4
  );

  const handleSave = async () => {
    setIsSaving(true);
    // 模拟保存
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    alert('校准已保存！');
  };

  // 模拟历史数据
  const historyData = [
    { date: '今天', mind: values.mind, body: values.body, spirit: values.spirit, vocation: values.vocation },
    { date: '昨天', mind: 65, body: 55, spirit: 70, vocation: 60 },
    { date: '前天', mind: 60, body: 58, spirit: 65, vocation: 55 },
  ];

  return (
    <div className="min-h-screen p-8">
      {/* 页面标题 */}
      <header className="mb-8 animate-fade-in-down">
        <h1 className="font-display text-3xl font-bold text-[var(--color-text-primary)] mb-2">
          H3 能量校准
        </h1>
        <p className="text-[var(--color-text-secondary)]">
          记录你的能量状态，保持对自我的觉察
        </p>
      </header>

      <div className="grid grid-cols-12 gap-6">
        {/* 主校准区域 */}
        <div className="col-span-12 lg:col-span-8">
          <GlassCard className="animate-fade-in-up">
            {/* 总分显示 */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-32 h-32 rounded-full border-4 border-[var(--color-primary)] mb-4">
                <span className="text-5xl font-bold text-[var(--color-primary)]">
                  {total}
                </span>
              </div>
              <p className="text-[var(--color-text-secondary)]">综合能量指数</p>
            </div>

            {/* 四维滑块 */}
            <div className="space-y-8">
              {h3Dimensions.map((dim) => {
                const value = values[dim.key as keyof typeof values];
                return (
                  <div key={dim.key} className="animate-fade-in-up">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{dim.icon}</span>
                        <div>
                          <h3 className="font-medium text-[var(--color-text-primary)]">
                            {dim.label}
                          </h3>
                          <p className="text-xs text-[var(--color-text-muted)]">
                            {dim.description}
                          </p>
                        </div>
                      </div>
                      <span
                        className="text-2xl font-bold"
                        style={{ color: dim.color }}
                      >
                        {value}%
                      </span>
                    </div>

                    {/* 滑块 */}
                    <div className="relative">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={value}
                        onChange={(e) =>
                          setValues({
                            ...values,
                            [dim.key]: Number(e.target.value),
                          })
                        }
                        className="w-full h-3 rounded-full appearance-none cursor-pointer"
                        style={{
                          background: `linear-gradient(to right, ${dim.color} 0%, ${dim.color} ${value}%, var(--color-bg-darker) ${value}%, var(--color-bg-darker) 100%)`,
                        }}
                      />
                      {/* 标记点 */}
                      <div className="flex justify-between px-1 mt-2">
                        {[0, 25, 50, 75, 100].map((mark) => (
                          <span
                            key={mark}
                            className="text-xs text-[var(--color-text-muted)]"
                          >
                            {mark}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 心情备注 */}
            <div className="mt-8 pt-8 border-t border-[var(--color-border-light)]">
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                今日心情备注（可选）
              </label>
              <textarea
                value={moodNote}
                onChange={(e) => setMoodNote(e.target.value)}
                placeholder="记录一下今天的状态..."
                rows={3}
                className="input w-full resize-none"
              />
            </div>

            {/* 保存按钮 */}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="btn btn-primary w-full mt-6 py-4"
            >
              {isSaving ? (
                <>
                  <span className="animate-spin">⏳</span>
                  保存中...
                </>
              ) : (
                <>
                  <Save size={18} />
                  保存校准
                </>
              )}
            </button>
          </GlassCard>
        </div>

        {/* 侧边信息 */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* 趋势分析 */}
          <GlassCard className="animate-fade-in-up delay-100">
            <h2 className="font-display text-lg font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
              <History size={20} />
              近期趋势
            </h2>

            <div className="space-y-4">
              {h3Dimensions.map((dim) => {
                const current = values[dim.key as keyof typeof values];
                const yesterday = historyData[1][dim.key as keyof typeof historyData[0]];
                const diff = current - (yesterday as number);
                
                return (
                  <div
                    key={dim.key}
                    className="flex items-center justify-between p-3 rounded-xl bg-[var(--color-bg-elevated)]"
                  >
                    <div className="flex items-center gap-2">
                      <span>{dim.icon}</span>
                      <span className="text-sm text-[var(--color-text-primary)]">
                        {dim.label}
                      </span>
                    </div>
                    <div
                      className={clsx(
                        'flex items-center gap-1 text-sm font-medium',
                        diff > 0
                          ? 'text-[var(--color-success)]'
                          : diff < 0
                          ? 'text-[var(--color-error)]'
                          : 'text-[var(--color-text-muted)]'
                      )}
                    >
                      {diff > 0 ? (
                        <TrendingUp size={16} />
                      ) : diff < 0 ? (
                        <TrendingDown size={16} />
                      ) : (
                        <Minus size={16} />
                      )}
                      {diff > 0 ? '+' : ''}
                      {diff}%
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>

          {/* 校准提示 */}
          <GlassCard className="animate-fade-in-up delay-200">
            <h2 className="font-display text-lg font-semibold text-[var(--color-text-primary)] mb-4">
              💡 校准提示
            </h2>
            <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)]">•</span>
                诚实评估你的当前状态
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)]">•</span>
                不需要追求完美的分数
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)]">•</span>
                关注趋势变化而非绝对值
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)]">•</span>
                每天同一时间校准效果更好
              </li>
            </ul>
          </GlassCard>

          {/* 历史记录预览 */}
          <GlassCard className="animate-fade-in-up delay-300">
            <h2 className="font-display text-lg font-semibold text-[var(--color-text-primary)] mb-4">
              📊 历史记录
            </h2>
            <div className="space-y-3">
              {historyData.slice(1).map((record, index) => (
                <div
                  key={index}
                  className="p-3 rounded-xl bg-[var(--color-bg-elevated)]"
                >
                  <p className="text-sm font-medium text-[var(--color-text-primary)] mb-2">
                    {record.date}
                  </p>
                  <div className="flex gap-2">
                    {h3Dimensions.map((dim) => (
                      <div
                        key={dim.key}
                        className="flex-1 h-2 rounded-full bg-[var(--color-bg-darker)]"
                      >
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${record[dim.key as keyof typeof record]}%`,
                            backgroundColor: dim.color,
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* 自定义滑块样式 */}
      <style>{`
        input[type="range"] {
          -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: var(--color-text-primary);
          cursor: pointer;
          border: 4px solid var(--color-bg-card);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
          transition: transform 0.15s ease;
        }
        
        input[type="range"]::-webkit-slider-thumb:hover {
          transform: scale(1.1);
        }
        
        input[type="range"]::-moz-range-thumb {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: var(--color-text-primary);
          cursor: pointer;
          border: 4px solid var(--color-bg-card);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
      `}</style>
    </div>
  );
}

