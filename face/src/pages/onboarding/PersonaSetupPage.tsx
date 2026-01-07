/**
 * 数字人格设定页面
 * 用户配置 AI 分身的称呼、指令、知识库等
 */
import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Sparkles,
  FileText,
  FileJson,
  Upload,
  Brain,
  Target,
  ArrowRight,
  ArrowLeft,
  X,
  Loader2,
  CheckCircle,
  Plus,
} from 'lucide-react';
import { useOnboardingStore } from '../../stores/useOnboardingStore';
import type { PersonaConfig } from '../../stores/useOnboardingStore';
import { useAuthStore } from '../../stores/useAuthStore';
import { api } from '../../lib/api';
import clsx from 'clsx';

// 默认 AI 人格选项
const personalityPresets = [
  {
    id: 'mentor',
    name: '导师型',
    desc: '严谨、富有洞察力，善于引导思考',
    prompt: '你是一位智慧的导师，善于通过提问引导用户深入思考，帮助他们发现自己的答案。',
  },
  {
    id: 'friend',
    name: '朋友型',
    desc: '温暖、理解、鼓励',
    prompt: '你是一位贴心的朋友，善于倾听和理解，在用户需要时给予温暖的支持和鼓励。',
  },
  {
    id: 'coach',
    name: '教练型',
    desc: '直接、高效、目标导向',
    prompt: '你是一位专业的教练，注重结果，善于帮助用户制定计划并推动执行。',
  },
  {
    id: 'custom',
    name: '自定义',
    desc: '完全自定义 AI 的人格',
    prompt: '',
  },
];

export default function PersonaSetupPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { setPersonaConfig, nextStep } = useOnboardingStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(1);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ id: string; name: string; status: 'uploading' | 'processing' | 'done' | 'error' }>>([]);
  
  const [formData, setFormData] = useState({
    nickname: user?.name || '',
    aiName: 'The Architect',
    selectedPersonality: 'mentor',
    customPersonality: '',
    instructions: '',
    vision: '',
    goals: [''],
  });

  const totalSteps = 4;

  const handlePersonalitySelect = (id: string) => {
    setFormData({
      ...formData,
      selectedPersonality: id,
      customPersonality: id === 'custom' ? formData.customPersonality : '',
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    for (const file of Array.from(files)) {
      const fileId = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      setUploadedFiles(prev => [...prev, { id: fileId, name: file.name, status: 'uploading' }]);

      try {
        // 创建 FormData
        const formDataUpload = new FormData();
        formDataUpload.append('file', file);
        
        // 1. 上传文件到后端
        const uploadResponse = await fetch('/api/upload', {
          method: 'POST',
          body: formDataUpload,
        });
        
        if (!uploadResponse.ok) {
          throw new Error('上传失败');
        }
        
        const uploadResult = await uploadResponse.json();
        
        // 2. 更新状态为处理中
        setUploadedFiles(prev =>
          prev.map(f => f.id === fileId ? { ...f, status: 'processing' } : f)
        );
        
        // 3. 触发记忆训练（将文件内容导入知识图谱）
        const trainResponse = await fetch('/api/train', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file_paths: [uploadResult.file_path],
          }),
        });
        
        if (!trainResponse.ok) {
          console.warn('记忆训练失败，但文件已上传');
        }

        setUploadedFiles(prev =>
          prev.map(f => f.id === fileId ? { ...f, status: 'done' } : f)
        );
      } catch (err) {
        console.error('文件处理失败:', err);
        setUploadedFiles(prev =>
          prev.map(f => f.id === fileId ? { ...f, status: 'error' } : f)
        );
      }
    }
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const addGoal = () => {
    setFormData({
      ...formData,
      goals: [...formData.goals, ''],
    });
  };

  const updateGoal = (index: number, value: string) => {
    const newGoals = [...formData.goals];
    newGoals[index] = value;
    setFormData({ ...formData, goals: newGoals });
  };

  const removeGoal = (index: number) => {
    if (formData.goals.length > 1) {
      setFormData({
        ...formData,
        goals: formData.goals.filter((_, i) => i !== index),
      });
    }
  };

  const handleNext = async () => {
    if (step < totalSteps) {
      setStep(step + 1);
    } else {
      // 保存配置到本地 store
      const selectedPreset = personalityPresets.find(p => p.id === formData.selectedPersonality);
      const config: PersonaConfig = {
        nickname: formData.nickname,
        aiName: formData.aiName,
        personality: formData.selectedPersonality === 'custom' 
          ? formData.customPersonality 
          : selectedPreset?.prompt || '',
        instructions: formData.instructions,
        knowledgeBase: [],
        memoryFiles: uploadedFiles.filter(f => f.status === 'done').map(f => f.id),
        vision: formData.vision,
        goals: formData.goals.filter(g => g.trim()),
      };
      
      setPersonaConfig(config);
      
      // 同步到后端
      try {
        // 1. 更新用户名称
        await api.patch('/auth/me', {
          name: formData.nickname,
        });
        
        // 2. 更新用户愿景
        await api.patch('/auth/me', {
          vision: {
            title: '我的5年愿景',
            description: formData.vision,
            core_values: [],
            key_milestones: formData.goals.filter(g => g.trim()),
          },
        });
        
        // 3. 更新数字人格配置
        // 将前端格式转换为后端格式
        const personaToneMap: Record<string, string> = {
          'mentor': 'mentor',
          'friend': 'partner',
          'coach': 'coach',
          'custom': 'mentor',
        };
        
        await api.put('/persona/current', {
          name: formData.aiName,
          tone: personaToneMap[formData.selectedPersonality] || 'mentor',
          system_prompt_template: formData.instructions || undefined,
          traits: selectedPreset?.desc ? [selectedPreset.desc] : [],
        });
      } catch (error) {
        console.error('同步配置到后端失败:', error);
        // 即使同步失败也继续引导流程
      }
      
      nextStep();
      navigate('/onboarding/h3');
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const isStepValid = () => {
    switch (step) {
      case 1:
        return formData.nickname.trim() && formData.aiName.trim();
      case 2:
        return formData.selectedPersonality !== 'custom' || formData.customPersonality.trim();
      case 3:
        return true; // 文件上传是可选的
      case 4:
        return formData.vision.trim();
      default:
        return false;
    }
  };

  return (
    <div className="onboarding-page">
      <div className="onboarding-background">
        <div className="onboarding-gradient" />
        <div className="onboarding-orb onboarding-orb-1" />
        <div className="onboarding-orb onboarding-orb-2" />
      </div>

      <div className="onboarding-container">
        {/* 进度指示器 */}
        <div className="onboarding-progress">
          <div className="onboarding-progress-bar">
            <div 
              className="onboarding-progress-fill" 
              style={{ width: `${(step / totalSteps) * 100}%` }}
            />
          </div>
          <span className="onboarding-progress-text">步骤 {step} / {totalSteps}</span>
        </div>

        {/* 步骤内容 */}
        <div className="onboarding-content">
          {/* 步骤 1: 基本信息 */}
          {step === 1 && (
            <div className="onboarding-step animate-fade-in-up">
              <div className="onboarding-icon">
                <User size={32} />
              </div>
              <h1 className="onboarding-title">让我们认识一下</h1>
              <p className="onboarding-desc">
                告诉我你希望如何被称呼，以及你想给你的 AI 分身起什么名字
              </p>

              <div className="onboarding-form">
                <div className="form-group">
                  <label className="form-label">你希望 AI 如何称呼你？</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="例如：小明、Alex"
                    value={formData.nickname}
                    onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">给你的 AI 分身起个名字</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="例如：The Architect、小助手"
                    value={formData.aiName}
                    onChange={(e) => setFormData({ ...formData, aiName: e.target.value })}
                  />
                  <p className="form-hint">这将是你数字分身的名字</p>
                </div>
              </div>
            </div>
          )}

          {/* 步骤 2: AI 人格 */}
          {step === 2 && (
            <div className="onboarding-step animate-fade-in-up">
              <div className="onboarding-icon">
                <Sparkles size={32} />
              </div>
              <h1 className="onboarding-title">选择 AI 人格</h1>
              <p className="onboarding-desc">
                选择一种与你最契合的 AI 人格风格
              </p>

              <div className="personality-grid">
                {personalityPresets.map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => handlePersonalitySelect(preset.id)}
                    className={clsx(
                      'personality-card',
                      formData.selectedPersonality === preset.id && 'personality-card-active'
                    )}
                  >
                    <span className="personality-name">{preset.name}</span>
                    <span className="personality-desc">{preset.desc}</span>
                    {formData.selectedPersonality === preset.id && (
                      <CheckCircle size={20} className="personality-check" />
                    )}
                  </button>
                ))}
              </div>

              {formData.selectedPersonality === 'custom' && (
                <div className="form-group mt-6">
                  <label className="form-label">自定义人格描述</label>
                  <textarea
                    className="form-textarea"
                    placeholder="描述你希望 AI 具有什么样的性格和行为方式..."
                    rows={4}
                    value={formData.customPersonality}
                    onChange={(e) => setFormData({ ...formData, customPersonality: e.target.value })}
                  />
                </div>
              )}

              <div className="form-group mt-6">
                <label className="form-label">特殊指令（可选）</label>
                <textarea
                  className="form-textarea"
                  placeholder="例如：每次对话结束时提醒我今天的目标、用简洁的语言回复..."
                  rows={3}
                  value={formData.instructions}
                  onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                />
              </div>
            </div>
          )}

          {/* 步骤 3: 记忆上传 */}
          {step === 3 && (
            <div className="onboarding-step animate-fade-in-up">
              <div className="onboarding-icon">
                <Brain size={32} />
              </div>
              <h1 className="onboarding-title">上传你的记忆</h1>
              <p className="onboarding-desc">
                上传日记、笔记、文档等，帮助 AI 更好地理解你
                <br />
                <span className="text-xs text-[var(--color-text-muted)]">
                  这些内容将被转化为长期记忆图谱
                </span>
              </p>

              <div 
                className="upload-area"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={40} className="upload-icon" />
                <p className="upload-text">点击或拖拽文件到此处</p>
                <p className="upload-hint">支持 PDF、TXT、MD、DOCX、JSON 格式</p>
                <p className="upload-hint" style={{ fontSize: '11px', marginTop: '4px', opacity: 0.7 }}>
                  可上传 ChatGPT 导出的对话记录 (conversations.json)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.txt,.md,.docx,.json"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </div>

              {uploadedFiles.length > 0 && (
                <div className="uploaded-files">
                  {uploadedFiles.map((file) => (
                    <div key={file.id} className="uploaded-file">
                      {file.name.endsWith('.json') ? (
                        <FileJson size={18} className="uploaded-file-icon" style={{ color: 'var(--color-warning)' }} />
                      ) : (
                        <FileText size={18} className="uploaded-file-icon" />
                      )}
                      <span className="uploaded-file-name">{file.name}</span>
                      <div className="uploaded-file-status">
                        {file.status === 'uploading' && <Loader2 size={16} className="animate-spin" />}
                        {file.status === 'processing' && <span className="text-xs text-[var(--color-warning)]">处理中...</span>}
                        {file.status === 'done' && <CheckCircle size={16} className="text-[var(--color-success)]" />}
                        {file.status === 'error' && <span className="text-xs text-[var(--color-error)]">失败</span>}
                      </div>
                      <button onClick={() => removeFile(file.id)} className="uploaded-file-remove">
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <p className="form-hint text-center mt-4">
                此步骤可跳过，后续可在设置中添加
              </p>
            </div>
          )}

          {/* 步骤 4: 愿景与目标 */}
          {step === 4 && (
            <div className="onboarding-step animate-fade-in-up">
              <div className="onboarding-icon">
                <Target size={32} />
              </div>
              <h1 className="onboarding-title">定义你的终局愿景</h1>
              <p className="onboarding-desc">
                描述你5年后想成为什么样的人，这将指引 AI 帮助你保持聚焦
              </p>

              <div className="onboarding-form">
                <div className="form-group">
                  <label className="form-label">你的终局愿景</label>
                  <textarea
                    className="form-textarea"
                    placeholder="5年后，我希望自己是一个..."
                    rows={4}
                    value={formData.vision}
                    onChange={(e) => setFormData({ ...formData, vision: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">核心目标（可添加多个）</label>
                  <div className="goals-list">
                    {formData.goals.map((goal, index) => (
                      <div key={index} className="goal-item">
                        <input
                          type="text"
                          className="form-input"
                          placeholder={`目标 ${index + 1}`}
                          value={goal}
                          onChange={(e) => updateGoal(index, e.target.value)}
                        />
                        {formData.goals.length > 1 && (
                          <button onClick={() => removeGoal(index)} className="goal-remove">
                            <X size={18} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <button onClick={addGoal} className="add-goal-btn">
                    <Plus size={18} />
                    添加目标
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 导航按钮 */}
        <div className="onboarding-nav">
          {step > 1 && (
            <button onClick={handleBack} className="onboarding-nav-btn onboarding-nav-back">
              <ArrowLeft size={20} />
              上一步
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={!isStepValid()}
            className="onboarding-nav-btn onboarding-nav-next"
          >
            {step === totalSteps ? '完成设置' : '下一步'}
            <ArrowRight size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

