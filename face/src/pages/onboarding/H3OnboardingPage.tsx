/**
 * H3 能量初始校准页面
 * 通过问卷评估用户当前的四维能量状态
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Brain,
  Heart,
  Flame,
  Briefcase,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  Sparkles,
} from 'lucide-react';
import { useOnboardingStore } from '../../stores/useOnboardingStore';
import type { H3InitialState } from '../../stores/useOnboardingStore';
import { useH3Store } from '../../stores/useH3Store';
import clsx from 'clsx';

// H3 维度配置
const dimensions = {
  mind: { name: '心智', icon: Brain, color: 'var(--color-h3-mind)' },
  body: { name: '身体', icon: Heart, color: 'var(--color-h3-body)' },
  spirit: { name: '精神', icon: Flame, color: 'var(--color-h3-spirit)' },
  vocation: { name: '志业', icon: Briefcase, color: 'var(--color-h3-vocation)' },
};

type DimensionKey = keyof typeof dimensions;

// 评估问题
interface Question {
  id: string;
  dimension: DimensionKey;
  text: string;
  options: { value: number; label: string }[];
}

const questions: Question[] = [
  // 心智维度 (3 题)
  {
    id: 'mind_1',
    dimension: 'mind',
    text: '最近一周，你的专注力如何？',
    options: [
      { value: 20, label: '很难集中注意力' },
      { value: 40, label: '偶尔能专注' },
      { value: 60, label: '大部分时间能专注' },
      { value: 80, label: '专注力很好' },
      { value: 100, label: '极度专注' },
    ],
  },
  {
    id: 'mind_2',
    dimension: 'mind',
    text: '你对新知识和技能的学习热情如何？',
    options: [
      { value: 20, label: '完全没有动力' },
      { value: 40, label: '偶尔有兴趣' },
      { value: 60, label: '保持基本的学习' },
      { value: 80, label: '积极主动学习' },
      { value: 100, label: '热情高涨' },
    ],
  },
  {
    id: 'mind_3',
    dimension: 'mind',
    text: '面对复杂问题时，你的思维清晰度如何？',
    options: [
      { value: 20, label: '混乱迷茫' },
      { value: 40, label: '有些困难' },
      { value: 60, label: '一般' },
      { value: 80, label: '比较清晰' },
      { value: 100, label: '非常清晰' },
    ],
  },
  // 身体维度 (3 题)
  {
    id: 'body_1',
    dimension: 'body',
    text: '你的睡眠质量如何？',
    options: [
      { value: 20, label: '严重失眠' },
      { value: 40, label: '睡眠不好' },
      { value: 60, label: '睡眠一般' },
      { value: 80, label: '睡眠良好' },
      { value: 100, label: '睡眠极佳' },
    ],
  },
  {
    id: 'body_2',
    dimension: 'body',
    text: '你的运动频率如何？',
    options: [
      { value: 20, label: '几乎不运动' },
      { value: 40, label: '偶尔运动' },
      { value: 60, label: '每周1-2次' },
      { value: 80, label: '每周3-4次' },
      { value: 100, label: '每天运动' },
    ],
  },
  {
    id: 'body_3',
    dimension: 'body',
    text: '你的整体精力水平如何？',
    options: [
      { value: 20, label: '经常疲惫' },
      { value: 40, label: '容易累' },
      { value: 60, label: '精力一般' },
      { value: 80, label: '精力充沛' },
      { value: 100, label: '活力满满' },
    ],
  },
  // 精神维度 (3 题)
  {
    id: 'spirit_1',
    dimension: 'spirit',
    text: '你对生活的满意度如何？',
    options: [
      { value: 20, label: '非常不满' },
      { value: 40, label: '不太满意' },
      { value: 60, label: '一般' },
      { value: 80, label: '比较满意' },
      { value: 100, label: '非常满意' },
    ],
  },
  {
    id: 'spirit_2',
    dimension: 'spirit',
    text: '你的情绪稳定性如何？',
    options: [
      { value: 20, label: '情绪波动大' },
      { value: 40, label: '有时焦虑' },
      { value: 60, label: '情绪一般' },
      { value: 80, label: '比较平和' },
      { value: 100, label: '内心平静' },
    ],
  },
  {
    id: 'spirit_3',
    dimension: 'spirit',
    text: '你与重要的人的关系如何？',
    options: [
      { value: 20, label: '关系紧张' },
      { value: 40, label: '有些疏远' },
      { value: 60, label: '关系一般' },
      { value: 80, label: '关系融洽' },
      { value: 100, label: '非常亲密' },
    ],
  },
  // 志业维度 (3 题)
  {
    id: 'vocation_1',
    dimension: 'vocation',
    text: '你对当前工作/事业的投入度如何？',
    options: [
      { value: 20, label: '完全没有动力' },
      { value: 40, label: '勉强应付' },
      { value: 60, label: '正常工作' },
      { value: 80, label: '积极投入' },
      { value: 100, label: '全力以赴' },
    ],
  },
  {
    id: 'vocation_2',
    dimension: 'vocation',
    text: '你的目标清晰度如何？',
    options: [
      { value: 20, label: '完全迷茫' },
      { value: 40, label: '有些模糊' },
      { value: 60, label: '大致清楚' },
      { value: 80, label: '比较清晰' },
      { value: 100, label: '非常明确' },
    ],
  },
  {
    id: 'vocation_3',
    dimension: 'vocation',
    text: '你最近的进步和成就感如何？',
    options: [
      { value: 20, label: '停滞不前' },
      { value: 40, label: '进展缓慢' },
      { value: 60, label: '稳步前进' },
      { value: 80, label: '进展顺利' },
      { value: 100, label: '突飞猛进' },
    ],
  },
];

export default function H3OnboardingPage() {
  const navigate = useNavigate();
  const { setH3InitialState, completeOnboarding } = useOnboardingStore();
  const { setScores: setH3Scores, initializeFromOnboarding } = useH3Store();

  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [showResult, setShowResult] = useState(false);

  const question = questions[currentQuestion];
  const progress = ((currentQuestion + 1) / questions.length) * 100;

  // 计算各维度分数
  const dimensionScores = useMemo(() => {
    const scores: Record<DimensionKey, number[]> = {
      mind: [],
      body: [],
      spirit: [],
      vocation: [],
    };

    questions.forEach((q) => {
      if (answers[q.id] !== undefined) {
        scores[q.dimension].push(answers[q.id]);
      }
    });

    const averages: Record<DimensionKey, number> = {
      mind: 0,
      body: 0,
      spirit: 0,
      vocation: 0,
    };

    (Object.keys(scores) as DimensionKey[]).forEach((dim) => {
      if (scores[dim].length > 0) {
        averages[dim] = Math.round(
          scores[dim].reduce((a, b) => a + b, 0) / scores[dim].length
        );
      }
    });

    return averages;
  }, [answers]);

  const totalScore = useMemo(() => {
    const values = Object.values(dimensionScores);
    if (values.every(v => v === 0)) return 0;
    return Math.round(values.reduce((a, b) => a + b, 0) / 4);
  }, [dimensionScores]);

  const handleAnswer = (value: number) => {
    setAnswers({ ...answers, [question.id]: value });
    
    if (currentQuestion < questions.length - 1) {
      setTimeout(() => {
        setCurrentQuestion(currentQuestion + 1);
      }, 300);
    } else {
      setShowResult(true);
    }
  };

  const handleBack = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const handleComplete = async () => {
    const h3State: H3InitialState = {
      mind: dimensionScores.mind,
      body: dimensionScores.body,
      spirit: dimensionScores.spirit,
      vocation: dimensionScores.vocation,
      answers,
      completedAt: new Date().toISOString(),
    };

    // 保存到 onboarding store（用于记录引导历史）
    setH3InitialState(h3State);
    
    // 同步到 H3 store（用于仪表盘显示）
    const h3Scores = {
      mind: dimensionScores.mind,
      body: dimensionScores.body,
      spirit: dimensionScores.spirit,
      vocation: dimensionScores.vocation,
    };
    setH3Scores(h3Scores);
    
    // 尝试同步到后端
    await initializeFromOnboarding(h3Scores);
    
    completeOnboarding();
    navigate('/dashboard');
  };

  if (showResult) {
    return (
      <div className="onboarding-page">
        <div className="onboarding-background">
          <div className="onboarding-gradient" />
          <div className="onboarding-orb onboarding-orb-1" />
          <div className="onboarding-orb onboarding-orb-2" />
        </div>

        <div className="onboarding-container">
          <div className="h3-result animate-fade-in-up">
            <div className="h3-result-header">
              <div className="h3-result-icon">
                <Sparkles size={40} />
              </div>
              <h1 className="h3-result-title">你的 H3 能量图谱</h1>
              <p className="h3-result-subtitle">
                基于你的回答，这是你当前的能量状态
              </p>
            </div>

            <div className="h3-result-score">
              <div className="h3-total-score">
                <span className="h3-total-value">{totalScore}</span>
                <span className="h3-total-label">综合能量</span>
              </div>
            </div>

            <div className="h3-dimensions">
              {(Object.keys(dimensions) as DimensionKey[]).map((dim) => {
                const { name, icon: Icon, color } = dimensions[dim];
                const score = dimensionScores[dim];
                return (
                  <div key={dim} className="h3-dimension-item">
                    <div className="h3-dimension-header">
                      <div className="h3-dimension-icon" style={{ backgroundColor: `${color}20`, color }}>
                        <Icon size={20} />
                      </div>
                      <span className="h3-dimension-name">{name}</span>
                      <span className="h3-dimension-score" style={{ color }}>{score}%</span>
                    </div>
                    <div className="h3-dimension-bar">
                      <div 
                        className="h3-dimension-fill" 
                        style={{ width: `${score}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="h3-result-message">
              <p>
                {totalScore >= 80 && '太棒了！你的能量状态非常好！继续保持！'}
                {totalScore >= 60 && totalScore < 80 && '不错！你的能量状态良好，还有提升空间。'}
                {totalScore >= 40 && totalScore < 60 && '你的能量状态一般，让我们一起努力提升。'}
                {totalScore < 40 && '你的能量状态需要关注，我会帮助你逐步改善。'}
              </p>
            </div>

            <button onClick={handleComplete} className="h3-result-btn">
              <CheckCircle size={20} />
              开始使用 Endgame OS
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-background">
        <div className="onboarding-gradient" />
        <div className="onboarding-orb onboarding-orb-1" />
        <div className="onboarding-orb onboarding-orb-2" />
      </div>

      <div className="onboarding-container">
        {/* 进度和维度指示 */}
        <div className="h3-header">
          <div className="h3-progress-bar">
            <div className="h3-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="h3-progress-info">
            <span className="h3-question-count">{currentQuestion + 1} / {questions.length}</span>
            <div 
              className="h3-dimension-badge"
              style={{ 
                backgroundColor: `${dimensions[question.dimension].color}20`,
                color: dimensions[question.dimension].color 
              }}
            >
              {dimensions[question.dimension].name}
            </div>
          </div>
        </div>

        {/* 问题卡片 */}
        <div className="h3-question-card animate-fade-in-up" key={question.id}>
          <h2 className="h3-question-text">{question.text}</h2>

          <div className="h3-options">
            {question.options.map((option) => (
              <button
                key={option.value}
                onClick={() => handleAnswer(option.value)}
                className={clsx(
                  'h3-option',
                  answers[question.id] === option.value && 'h3-option-selected'
                )}
              >
                <span className="h3-option-label">{option.label}</span>
                {answers[question.id] === option.value && (
                  <CheckCircle size={20} className="h3-option-check" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* 导航 */}
        {currentQuestion > 0 && (
          <button onClick={handleBack} className="h3-back-btn">
            <ArrowLeft size={20} />
            上一题
          </button>
        )}
      </div>
    </div>
  );
}

