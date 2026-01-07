/**
 * 设置页面
 * 允许用户编辑数字人格配置、愿景、目标等
 */
import { useState, useEffect } from 'react';
import {
  User,
  Sparkles,
  Target,
  Brain,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import { useAuthStore } from '../stores/useAuthStore';
import { api } from '../lib/api';
import clsx from 'clsx';

interface PersonaConfig {
  name: string;
  tone: 'mentor' | 'coach' | 'partner' | 'analyst';
  proactive_level: number;
  challenge_mode: boolean;
  system_prompt_template?: string;
  traits: string[];
}

interface UserVision {
  title: string;
  description: string;
  core_values: string[];
  key_milestones: string[];
}

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'persona' | 'vision' | 'profile'>('persona');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Persona 配置状态
  const [personaConfig, setPersonaConfig] = useState<PersonaConfig>({
    name: 'The Architect',
    tone: 'mentor',
    proactive_level: 3,
    challenge_mode: true,
    system_prompt_template: '',
    traits: [],
  });

  // Vision 配置状态
  const [vision, setVision] = useState<UserVision>({
    title: '',
    description: '',
    core_values: [],
    key_milestones: [],
  });

  // Profile 配置状态
  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
  });

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);

        // 加载用户信息
        const userData = await api.get('/auth/me');
        if (userData) {
          setProfile({
            name: userData.name || '',
            email: userData.email || '',
          });

          // 加载愿景
          if (userData.vision) {
            setVision({
              title: userData.vision.title || '',
              description: userData.vision.description || '',
              core_values: userData.vision.core_values || [],
              key_milestones: userData.vision.key_milestones || [],
            });
          }
        }

        // 加载数字人格配置
        const personaData = await api.get('/persona/current');
        if (personaData) {
          setPersonaConfig({
            name: personaData.name || 'The Architect',
            tone: personaData.tone || 'mentor',
            proactive_level: personaData.proactive_level || 3,
            challenge_mode: personaData.challenge_mode ?? true,
            system_prompt_template: personaData.system_prompt_template || '',
            traits: personaData.traits || [],
          });
        }
      } catch (error) {
        console.error('加载设置数据失败:', error);
        setSaveStatus('error');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // 保存 Persona 配置
  const handleSavePersona = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');

      await api.put('/persona/current', personaConfig);

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('保存数字人格配置失败:', error);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  // 保存 Vision 配置
  const handleSaveVision = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');

      await api.patch('/auth/me', {
        vision: vision,
      });

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('保存愿景配置失败:', error);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  // 保存 Profile 配置
  const handleSaveProfile = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');

      await api.patch('/auth/me', {
        name: profile.name,
      });

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('保存个人信息失败:', error);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  // 添加目标
  const addMilestone = () => {
    setVision({
      ...vision,
      key_milestones: [...vision.key_milestones, ''],
    });
  };

  // 更新目标
  const updateMilestone = (index: number, value: string) => {
    const newMilestones = [...vision.key_milestones];
    newMilestones[index] = value;
    setVision({ ...vision, key_milestones: newMilestones });
  };

  // 删除目标
  const removeMilestone = (index: number) => {
    setVision({
      ...vision,
      key_milestones: vision.key_milestones.filter((_, i) => i !== index),
    });
  };

  // 添加特征
  const addTrait = () => {
    setPersonaConfig({
      ...personaConfig,
      traits: [...personaConfig.traits, ''],
    });
  };

  // 更新特征
  const updateTrait = (index: number, value: string) => {
    const newTraits = [...personaConfig.traits];
    newTraits[index] = value;
    setPersonaConfig({ ...personaConfig, traits: newTraits });
  };

  // 删除特征
  const removeTrait = (index: number) => {
    setPersonaConfig({
      ...personaConfig,
      traits: personaConfig.traits.filter((_, i) => i !== index),
    });
  };

  if (isLoading) {
    return (
      <div className="page-container">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--color-primary)]" />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <header className="page-header animate-fade-in-down">
        <h1 className="page-title">设置</h1>
        <p className="page-subtitle">管理你的数字人格、愿景和个人信息</p>
      </header>

      {/* 标签页导航 */}
      <div className="mb-6 flex gap-2 border-b border-[var(--color-border)]">
        {[
          { id: 'persona', label: '数字人格', icon: Sparkles },
          { id: 'vision', label: '终局愿景', icon: Target },
          { id: 'profile', label: '个人信息', icon: User },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={clsx(
                'px-6 py-3 text-sm font-medium transition-all relative',
                activeTab === tab.id
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
              )}
            >
              <div className="flex items-center gap-2">
                <Icon size={18} />
                <span>{tab.label}</span>
              </div>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
              )}
            </button>
          );
        })}
      </div>

      {/* 保存状态提示 */}
      {saveStatus !== 'idle' && (
        <div
          className={clsx(
            'mb-6 p-4 rounded-xl flex items-center gap-3 animate-fade-in-down',
            saveStatus === 'success'
              ? 'bg-[var(--color-success)]/20 border border-[var(--color-success)]/40'
              : 'bg-[var(--color-error)]/20 border border-[var(--color-error)]/40'
          )}
        >
          {saveStatus === 'success' ? (
            <CheckCircle className="text-[var(--color-success)]" size={20} />
          ) : (
            <AlertCircle className="text-[var(--color-error)]" size={20} />
          )}
          <span
            className={clsx(
              'text-sm',
              saveStatus === 'success'
                ? 'text-[var(--color-success)]'
                : 'text-[var(--color-error)]'
            )}
          >
            {saveStatus === 'success' ? '保存成功' : '保存失败，请重试'}
          </span>
        </div>
      )}

      {/* 数字人格配置 */}
      {activeTab === 'persona' && (
        <div className="space-y-6 animate-fade-in-up">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <Brain className="text-[var(--color-primary)]" size={24} />
              <h2 className="font-display text-xl font-semibold text-[var(--color-text-primary)]">
                数字人格配置
              </h2>
            </div>

            <div className="space-y-6">
              {/* AI 名称 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  AI 名称
                </label>
                <input
                  type="text"
                  value={personaConfig.name}
                  onChange={(e) =>
                    setPersonaConfig({ ...personaConfig, name: e.target.value })
                  }
                  className="input w-full"
                  placeholder="例如: The Architect"
                />
              </div>

              {/* 语气风格 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  语气风格
                </label>
                <select
                  value={personaConfig.tone}
                  onChange={(e) =>
                    setPersonaConfig({
                      ...personaConfig,
                      tone: e.target.value as any,
                    })
                  }
                  className="input w-full"
                >
                  <option value="mentor">导师型 - 温和引导</option>
                  <option value="coach">教练型 - 激励推动</option>
                  <option value="partner">伙伴型 - 平等交流</option>
                  <option value="analyst">分析型 - 理性客观</option>
                </select>
              </div>

              {/* 主动性级别 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  主动性级别: {personaConfig.proactive_level}/5
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={personaConfig.proactive_level}
                  onChange={(e) =>
                    setPersonaConfig({
                      ...personaConfig,
                      proactive_level: parseInt(e.target.value),
                    })
                  }
                  className="w-full"
                />
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  控制 AI 主动提问和建议的频率
                </p>
              </div>

              {/* 挑战模式 */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="challenge_mode"
                  checked={personaConfig.challenge_mode}
                  onChange={(e) =>
                    setPersonaConfig({
                      ...personaConfig,
                      challenge_mode: e.target.checked,
                    })
                  }
                  className="w-5 h-5 rounded border-[var(--color-border)]"
                />
                <label
                  htmlFor="challenge_mode"
                  className="text-sm text-[var(--color-text-primary)]"
                >
                  启用挑战模式（AI 会主动挑战你的舒适区）
                </label>
              </div>

              {/* 自定义系统提示词 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  自定义系统提示词（可选）
                </label>
                <textarea
                  value={personaConfig.system_prompt_template || ''}
                  onChange={(e) =>
                    setPersonaConfig({
                      ...personaConfig,
                      system_prompt_template: e.target.value,
                    })
                  }
                  className="input w-full min-h-[120px]"
                  placeholder="自定义 AI 的行为和响应方式..."
                />
              </div>

              {/* 特征标签 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  特征标签
                </label>
                <div className="space-y-2">
                  {personaConfig.traits.map((trait, index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={trait}
                        onChange={(e) => updateTrait(index, e.target.value)}
                        className="input flex-1"
                        placeholder="例如: 智慧、耐心、引导"
                      />
                      <button
                        onClick={() => removeTrait(index)}
                        className="btn btn-secondary px-3"
                      >
                        删除
                      </button>
                    </div>
                  ))}
                  <button onClick={addTrait} className="btn btn-secondary w-full">
                    + 添加特征
                  </button>
                </div>
              </div>

              {/* 保存按钮 */}
              <button
                onClick={handleSavePersona}
                disabled={isSaving}
                className="btn btn-primary w-full"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save size={18} />
                    保存配置
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {/* 终局愿景配置 */}
      {activeTab === 'vision' && (
        <div className="space-y-6 animate-fade-in-up">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <Target className="text-[var(--color-primary)]" size={24} />
              <h2 className="font-display text-xl font-semibold text-[var(--color-text-primary)]">
                5年终局愿景
              </h2>
            </div>

            <div className="space-y-6">
              {/* 愿景标题 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  愿景标题
                </label>
                <input
                  type="text"
                  value={vision.title}
                  onChange={(e) =>
                    setVision({ ...vision, title: e.target.value })
                  }
                  className="input w-full"
                  placeholder="例如: 成为独立创业者"
                />
              </div>

              {/* 愿景描述 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  愿景详细描述
                </label>
                <textarea
                  value={vision.description}
                  onChange={(e) =>
                    setVision({ ...vision, description: e.target.value })
                  }
                  className="input w-full min-h-[150px]"
                  placeholder="详细描述你的5年愿景..."
                />
              </div>

              {/* 关键里程碑 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  关键里程碑
                </label>
                <div className="space-y-2">
                  {vision.key_milestones.map((milestone, index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={milestone}
                        onChange={(e) => updateMilestone(index, e.target.value)}
                        className="input flex-1"
                        placeholder="例如: 第一年: 完成 MVP"
                      />
                      <button
                        onClick={() => removeMilestone(index)}
                        className="btn btn-secondary px-3"
                      >
                        删除
                      </button>
                    </div>
                  ))}
                  <button onClick={addMilestone} className="btn btn-secondary w-full">
                    + 添加里程碑
                  </button>
                </div>
              </div>

              {/* 保存按钮 */}
              <button
                onClick={handleSaveVision}
                disabled={isSaving}
                className="btn btn-primary w-full"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save size={18} />
                    保存愿景
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {/* 个人信息配置 */}
      {activeTab === 'profile' && (
        <div className="space-y-6 animate-fade-in-up">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <User className="text-[var(--color-primary)]" size={24} />
              <h2 className="font-display text-xl font-semibold text-[var(--color-text-primary)]">
                个人信息
              </h2>
            </div>

            <div className="space-y-6">
              {/* 用户名称 */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  显示名称
                </label>
                <input
                  type="text"
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="input w-full"
                  placeholder="你的名字"
                />
              </div>

              {/* 邮箱（只读） */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
                  邮箱地址
                </label>
                <input
                  type="email"
                  value={profile.email}
                  disabled
                  className="input w-full bg-[var(--color-bg-darker)] opacity-50 cursor-not-allowed"
                />
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  邮箱地址无法修改
                </p>
              </div>

              {/* 保存按钮 */}
              <button
                onClick={handleSaveProfile}
                disabled={isSaving}
                className="btn btn-primary w-full"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save size={18} />
                    保存个人信息
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}

