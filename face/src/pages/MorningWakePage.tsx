/**
 * 晨间唤醒页面
 * 按照原型图 Layout 3 设计
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sun,
  Moon,
  Battery,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import { useAuthStore } from '../stores/useAuthStore';
import clsx from 'clsx';

// H3 维度配置
const h3Dimensions = [
  { key: 'mind', label: '心智', color: 'var(--color-h3-mind)', icon: '🧠' },
  { key: 'body', label: '身体', color: 'var(--color-h3-body)', icon: '💪' },
  { key: 'spirit', label: '精神', color: 'var(--color-h3-spirit)', icon: '✨' },
  { key: 'vocation', label: '志业', color: 'var(--color-h3-vocation)', icon: '🎯' },
];

// 模拟昨日数据
const yesterdayData = {
  h3: { mind: 65, body: 55, spirit: 70, vocation: 60 },
  conversations: 3,
  tasksCompleted: 2,
  highlights: ['完成了项目文档', '进行了有效的反思对话'],
};

export default function MorningWakePage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [step, setStep] = useState(0); // 0: 欢迎, 1: 昨日回顾, 2: 今日校准, 3: AI 唤醒
  const [todayH3, setTodayH3] = useState({
    mind: 50,
    body: 50,
    spirit: 50,
    vocation: 50,
  });
  const [sleepQuality, setSleepQuality] = useState(3);
  const [energyLevel, setEnergyLevel] = useState(3);

  const [greeting, setGreeting] = useState('');
  const [showAIMessage, setShowAIMessage] = useState(false);

  // 生成问候语
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 6) setGreeting('夜深了，还没休息吗');
    else if (hour < 9) setGreeting('早安');
    else if (hour < 12) setGreeting('上午好');
    else setGreeting('你好');
  }, []);

  // AI 消息逐字显示
  const aiMessage = `${greeting}，${user?.name || '朋友'}！

根据昨日数据，你的能量状态整体保持稳定。今天建议：

1. 💡 心智状态良好，适合处理复杂任务
2. 💪 身体能量略有下降，记得适当休息
3. ✨ 精神状态优秀，保持这种积极心态
4. 🎯 志业进展稳定，继续推进核心目标

今天，让我们继续向终局愿景前进！`;

  const [displayedMessage, setDisplayedMessage] = useState('');

  useEffect(() => {
    if (step === 3 && showAIMessage) {
      let index = 0;
      const interval = setInterval(() => {
        if (index < aiMessage.length) {
          setDisplayedMessage(aiMessage.slice(0, index + 1));
          index++;
        } else {
          clearInterval(interval);
        }
      }, 30);
      return () => clearInterval(interval);
    }
  }, [step, showAIMessage, aiMessage]);

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
      if (step === 2) {
        setTimeout(() => setShowAIMessage(true), 500);
      }
    } else {
      navigate('/dashboard');
    }
  };

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <div className="text-center animate-fade-in">
            {/* 日出/日落图标 */}
            <div className="w-32 h-32 mx-auto mb-8 relative">
              <div className="absolute inset-0 rounded-full bg-gradient-to-b from-[var(--color-warning)] to-[var(--color-primary)] opacity-20 animate-pulse" />
              <div className="absolute inset-4 rounded-full bg-[var(--color-bg-card)] flex items-center justify-center">
                <Sun size={48} className="text-[var(--color-warning)]" />
              </div>
            </div>

            <h1 className="font-display text-4xl font-bold text-[var(--color-text-primary)] mb-4">
              {greeting}，{user?.name || '朋友'}
            </h1>
            <p className="text-xl text-[var(--color-text-secondary)] mb-8">
              新的一天，新的可能
            </p>

            <button onClick={handleNext} className="btn btn-primary btn-lg">
              开始晨间唤醒
              <ArrowRight size={20} />
            </button>
          </div>
        );

      case 1:
        return (
          <div className="animate-fade-in">
            <h2 className="font-display text-2xl font-bold text-[var(--color-text-primary)] mb-6 text-center">
              📊 昨日回顾
            </h2>

            {/* 昨日 H3 状态 */}
            <GlassCard className="mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-4">
                昨日能量状态
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {h3Dimensions.map((dim) => {
                  const value = yesterdayData.h3[dim.key as keyof typeof yesterdayData.h3];
                  return (
                    <div key={dim.key} className="flex items-center gap-3">
                      <span className="text-xl">{dim.icon}</span>
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-sm text-[var(--color-text-secondary)]">
                            {dim.label}
                          </span>
                          <span className="text-sm font-medium" style={{ color: dim.color }}>
                            {value}%
                          </span>
                        </div>
                        <div className="h-2 bg-[var(--color-bg-darker)] rounded-full">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${value}%`, backgroundColor: dim.color }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassCard>

            {/* 昨日成就 */}
            <GlassCard className="mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-4">
                昨日成就
              </h3>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="p-4 rounded-xl bg-[var(--color-bg-elevated)]">
                  <p className="text-2xl font-bold text-[var(--color-primary)]">
                    {yesterdayData.conversations}
                  </p>
                  <p className="text-sm text-[var(--color-text-muted)]">对话数</p>
                </div>
                <div className="p-4 rounded-xl bg-[var(--color-bg-elevated)]">
                  <p className="text-2xl font-bold text-[var(--color-success)]">
                    {yesterdayData.tasksCompleted}
                  </p>
                  <p className="text-sm text-[var(--color-text-muted)]">完成任务</p>
                </div>
              </div>
              <ul className="space-y-2">
                {yesterdayData.highlights.map((highlight, index) => (
                  <li key={index} className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                    <span className="text-[var(--color-success)]">✓</span>
                    {highlight}
                  </li>
                ))}
              </ul>
            </GlassCard>

            <button onClick={handleNext} className="btn btn-primary w-full">
              继续
              <ArrowRight size={18} />
            </button>
          </div>
        );

      case 2:
        return (
          <div className="animate-fade-in">
            <h2 className="font-display text-2xl font-bold text-[var(--color-text-primary)] mb-6 text-center">
              ⚡ 今日能量校准
            </h2>

            {/* 睡眠质量 */}
            <GlassCard className="mb-6">
              <div className="flex items-center gap-4 mb-4">
                <Moon size={24} className="text-[var(--color-primary)]" />
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)]">
                    昨晚睡眠质量
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    1 = 很差, 5 = 很好
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((level) => (
                  <button
                    key={level}
                    onClick={() => setSleepQuality(level)}
                    className={clsx(
                      'flex-1 py-3 rounded-xl font-medium transition-all',
                      sleepQuality === level
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card-hover)]'
                    )}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </GlassCard>

            {/* 起床精力 */}
            <GlassCard className="mb-6">
              <div className="flex items-center gap-4 mb-4">
                <Battery size={24} className="text-[var(--color-success)]" />
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)]">
                    起床时精力
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    1 = 很疲惫, 5 = 精力充沛
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((level) => (
                  <button
                    key={level}
                    onClick={() => setEnergyLevel(level)}
                    className={clsx(
                      'flex-1 py-3 rounded-xl font-medium transition-all',
                      energyLevel === level
                        ? 'bg-[var(--color-success)] text-white'
                        : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card-hover)]'
                    )}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </GlassCard>

            {/* H3 快速校准 */}
            <GlassCard className="mb-6">
              <h3 className="font-medium text-[var(--color-text-primary)] mb-4">
                快速能量评估
              </h3>
              <div className="space-y-4">
                {h3Dimensions.map((dim) => (
                  <div key={dim.key}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-[var(--color-text-secondary)]">
                        {dim.icon} {dim.label}
                      </span>
                      <span
                        className="text-sm font-medium"
                        style={{ color: dim.color }}
                      >
                        {todayH3[dim.key as keyof typeof todayH3]}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={todayH3[dim.key as keyof typeof todayH3]}
                      onChange={(e) =>
                        setTodayH3({
                          ...todayH3,
                          [dim.key]: Number(e.target.value),
                        })
                      }
                      className="w-full h-2 rounded-full appearance-none cursor-pointer"
                      style={{
                        background: `linear-gradient(to right, ${dim.color} 0%, ${dim.color} ${
                          todayH3[dim.key as keyof typeof todayH3]
                        }%, var(--color-bg-darker) ${
                          todayH3[dim.key as keyof typeof todayH3]
                        }%, var(--color-bg-darker) 100%)`,
                      }}
                    />
                  </div>
                ))}
              </div>
            </GlassCard>

            <button onClick={handleNext} className="btn btn-primary w-full">
              完成校准
              <Sparkles size={18} />
            </button>
          </div>
        );

      case 3:
        return (
          <div className="animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-[var(--color-primary)] flex items-center justify-center shadow-[var(--shadow-glow-lg)]">
                <Sparkles size={40} className="text-white" />
              </div>
              <h2 className="font-display text-2xl font-bold text-[var(--color-text-primary)]">
                The Architect 的晨间问候
              </h2>
            </div>

            <GlassCard className="mb-8">
              <div className="prose prose-invert max-w-none">
                <p className="text-[var(--color-text-primary)] whitespace-pre-line leading-relaxed">
                  {displayedMessage}
                  {displayedMessage.length < aiMessage.length && (
                    <span className="inline-block w-2 h-4 ml-1 bg-[var(--color-primary)] animate-pulse" />
                  )}
                </p>
              </div>
            </GlassCard>

            {displayedMessage.length >= aiMessage.length && (
              <button
                onClick={handleNext}
                className="btn btn-primary w-full animate-fade-in"
              >
                开始今天的旅程
                <ArrowRight size={18} />
              </button>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-dark)] flex items-center justify-center p-8">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--color-primary)] opacity-5 rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-[var(--color-warning)] opacity-5 rounded-full blur-[80px]" />
      </div>

      {/* 主内容 */}
      <div className="relative z-10 w-full max-w-lg">
        {/* 进度指示器 */}
        <div className="flex justify-center gap-2 mb-8">
          {[0, 1, 2, 3].map((s) => (
            <div
              key={s}
              className={clsx(
                'w-2 h-2 rounded-full transition-all',
                s === step
                  ? 'w-8 bg-[var(--color-primary)]'
                  : s < step
                  ? 'bg-[var(--color-primary)]'
                  : 'bg-[var(--color-border)]'
              )}
            />
          ))}
        </div>

        {renderStep()}

        {/* 跳过按钮 */}
        {step < 3 && (
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-6 w-full text-center text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
          >
            跳过晨间唤醒
          </button>
        )}
      </div>

      {/* 滑块样式 */}
      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: var(--color-text-primary);
          cursor: pointer;
          border: 3px solid var(--color-bg-card);
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
        }
      `}</style>
    </div>
  );
}

