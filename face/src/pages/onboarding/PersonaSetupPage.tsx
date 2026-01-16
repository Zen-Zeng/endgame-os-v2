/**
 * 数字人格设定页面
 * 用户配置 AI 分身的称呼、指令、知识库等
 */
import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User as UserIcon,
  Sparkles,
  FileText,
  Upload,
  Brain,
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
import GlassCard from '../../components/layout/GlassCard';
import Button from '../../components/ui/Button';
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

interface PersonaSetupPageProps {
  mode?: 'onboarding' | 'settings';
}

export default function PersonaSetupPage({ mode = 'onboarding' }: PersonaSetupPageProps) {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { setPersonaConfig, nextStep } = useOnboardingStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(1);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ id: string; name: string; status: 'uploading' | 'processing' | 'done' | 'error' }>>([]);
  
  const [formData, setFormData] = useState({
    nickname: user?.name || '',
    aiName: user?.persona?.name || 'The Architect',
    selectedPersonality: 'mentor',
    customPersonality: user?.persona?.system_prompt_template || '',
    instructions: user?.persona?.system_prompt_template || '',
    vision: user?.vision?.description || '',
    goals: user?.vision?.key_milestones || [''],
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
        
        // 1. 上传文件到后端 (会自动触发记忆摄取任务)
        // 返回 ArchiveFile 对象，包含 stored_name (filename)
        const uploadResult = await api.post<any>('/archives/upload', formDataUpload);
        
        // 2. 更新状态为处理中
        setUploadedFiles(prev =>
          prev.map(f => f.id === fileId ? { ...f, status: 'processing' } : f)
        );
        
        // 3. 模拟等待处理完成 (实际处理在后台进行)
        // 如果需要精确状态，应该轮询 /archives/files/{id} 查看 is_processed 字段
        await new Promise(resolve => setTimeout(resolve, 1500));

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
        memoryFiles: uploadedFiles.filter((f: any) => f.status === 'done').map((f: any) => f.id),
        vision: formData.vision,
        goals: formData.goals.filter((g: string) => g.trim()),
      };
      
      setPersonaConfig(config);
      
      // 同步到后端
      try {
        const personaToneMap: Record<string, string> = {
          'mentor': 'mentor',
          'friend': 'partner',
          'coach': 'coach',
          'custom': 'mentor',
        };

        if (mode === 'settings') {
          // 更新模式：调用 /persona/current
          await api.put('/persona/current', {
            name: formData.aiName,
            tone: personaToneMap[formData.selectedPersonality] || 'mentor',
            system_prompt_template: formData.instructions || undefined,
            traits: selectedPreset?.desc ? [selectedPreset.desc] : [],
          });
        } else {
          // 初始化模式
          await api.post('/auth/initialize', {
            name: formData.nickname,
            vision: {
              title: '我的5年愿景',
              description: formData.vision,
              core_values: [],
              key_milestones: formData.goals.filter((g: string) => g.trim()),
            },
            persona: {
              name: formData.aiName,
              tone: personaToneMap[formData.selectedPersonality] || 'mentor',
              system_prompt_template: formData.instructions || undefined,
              traits: selectedPreset?.desc ? [selectedPreset.desc] : [],
            }
          });
        }
      } catch (error) {
        console.error('保存配置失败:', error);
      }
      
      if (mode === 'settings') {
        navigate('/');
      } else {
        nextStep();
        navigate('/onboarding/h3');
      }
    }
  };

  return (
    <div className="min-h-screen bg-[var(--md-sys-color-background)] flex flex-col p-6 lg:p-12 relative overflow-hidden">
      {/* 装饰背景 */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[var(--md-sys-color-primary)] opacity-5 blur-[120px] rounded-full -z-10" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-[var(--md-sys-color-secondary)] opacity-5 blur-[120px] rounded-full -z-10" />

      {/* 顶部导航 */}
      <div className="max-w-4xl mx-auto w-full flex justify-between items-center mb-12">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-primary)] flex items-center justify-center text-white">
            <Sparkles size={24} />
          </div>
          <h1 className="text-2xl font-black tracking-tighter">{mode === 'settings' ? '系统设置' : '人格设定'}</h1>
        </div>

        {mode === 'settings' && (
          <button 
            onClick={() => navigate('/')}
            className="p-2 rounded-full hover:bg-[var(--md-sys-color-surface-container-high)] transition-colors"
            title="返回系统"
          >
            <X size={24} />
          </button>
        )}
        
        {/* 进度指示器 */}
        <div className="flex items-center gap-2">
          {Array.from({ length: totalSteps }).map((_, i: number) => (
            <div 
              key={i} 
              className={clsx(
                "h-1.5 rounded-full transition-all duration-500",
                i + 1 === step ? "w-8 bg-[var(--md-sys-color-primary)]" : 
                i + 1 < step ? "w-4 bg-[var(--md-sys-color-primary)] opacity-30" : "w-4 bg-[var(--md-sys-color-outline-variant)]"
              )}
            />
          ))}
        </div>
      </div>

      <main className="max-w-4xl mx-auto w-full flex-1 flex flex-col justify-center">
        <GlassCard className="p-10 border-[var(--md-sys-color-outline-variant)]">
          {/* 步骤内容渲染 */}
          {step === 1 && (
            <div className="animate-fade-in space-y-8">
              <div className="text-center max-w-lg mx-auto mb-10">
                <h2 className="text-4xl font-black tracking-tighter mb-4">基本信息</h2>
                <p className="text-[var(--md-sys-color-on-surface-variant)] opacity-60">定义你和你的数字分身如何互相称呼。</p>
              </div>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">你的称呼</label>
                  <div className="relative">
                    <UserIcon className="absolute left-5 top-1/2 -translate-y-1/2 opacity-30" size={20} />
                    <input
                      type="text"
                      className="w-full pl-14 pr-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all"
                      value={formData.nickname}
                      onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                      placeholder="例如：岳"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">AI 分身名称</label>
                  <div className="relative">
                    <Brain className="absolute left-5 top-1/2 -translate-y-1/2 opacity-30" size={20} />
                    <input
                      type="text"
                      className="w-full pl-14 pr-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all"
                      value={formData.aiName}
                      onChange={(e) => setFormData({ ...formData, aiName: e.target.value })}
                      placeholder="例如：The Architect"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="animate-fade-in space-y-8">
              <div className="text-center max-w-lg mx-auto mb-10">
                <h2 className="text-4xl font-black tracking-tighter mb-4">性格底色</h2>
                <p className="text-[var(--md-sys-color-on-surface-variant)] opacity-60">选择一个最能产生共鸣的交互风格。</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {personalityPresets.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => handlePersonalitySelect(p.id)}
                    className={clsx(
                      "p-6 rounded-2xl border text-left transition-all group",
                      formData.selectedPersonality === p.id 
                        ? "bg-[var(--md-sys-color-primary-container)] border-[var(--md-sys-color-primary)]" 
                        : "bg-[var(--md-sys-color-surface-container-low)] border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container-high)]"
                    )}
                  >
                    <h3 className={clsx(
                      "font-bold mb-1 transition-colors",
                      formData.selectedPersonality === p.id ? "text-[var(--md-sys-color-on-primary-container)]" : "text-[var(--md-sys-color-on-surface)]"
                    )}>{p.name}</h3>
                    <p className="text-sm opacity-60">{p.desc}</p>
                  </button>
                ))}
              </div>

              {formData.selectedPersonality === 'custom' && (
                <div className="animate-fade-in-up space-y-3">
                  <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">自定义人格指令</label>
                  <textarea
                    className="w-full px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all min-h-[120px] resize-none"
                    placeholder="描述你希望 AI 表现出的性格特征..."
                    value={formData.customPersonality}
                    onChange={(e) => setFormData({ ...formData, customPersonality: e.target.value })}
                  />
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="animate-fade-in space-y-8">
              <div className="text-center max-w-lg mx-auto mb-10">
                <h2 className="text-4xl font-black tracking-tighter mb-4">知识摄取</h2>
                <p className="text-[var(--md-sys-color-on-surface-variant)] opacity-60">上传你的笔记、日记或项目文档，让 AI 拥有你的记忆。</p>
              </div>

              <div 
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-[var(--md-sys-color-outline-variant)] rounded-3xl p-12 text-center cursor-pointer hover:border-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-primary-container)]/10 transition-all group"
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileUpload} 
                  multiple 
                  className="hidden" 
                />
                <div className="w-16 h-16 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                  <Upload className="text-[var(--md-sys-color-primary)]" size={32} />
                </div>
                <h3 className="font-bold text-lg mb-1">点击或拖拽上传文件</h3>
                <p className="text-sm opacity-50">支持 PDF, TXT, MD, DOCX (最大 20MB)</p>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="grid gap-3">
                  {uploadedFiles.map((file) => (
                    <div key={file.id} className="flex items-center justify-between p-4 rounded-2xl bg-[var(--md-sys-color-surface-container-low)] border border-[var(--md-sys-color-outline-variant)]">
                      <div className="flex items-center gap-4">
                        <FileText size={20} className="text-[var(--md-sys-color-primary)]" />
                        <div>
                          <p className="text-sm font-bold">{file.name}</p>
                          <p className="text-[10px] uppercase tracking-widest opacity-40">{file.status}</p>
                        </div>
                      </div>
                      {file.status === 'done' ? (
                        <CheckCircle className="text-green-500" size={20} />
                      ) : (
                        <Loader2 className="animate-spin opacity-30" size={20} />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 4 && (
            <div className="animate-fade-in space-y-8">
              <div className="text-center max-w-lg mx-auto mb-10">
                <h2 className="text-4xl font-black tracking-tighter mb-4">终局愿景</h2>
                <p className="text-[var(--md-sys-color-on-surface-variant)] opacity-60">在这个系统中，你最希望达成的长期目标是什么？</p>
              </div>

              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">长期愿景 (Vision)</label>
                  <textarea
                    className="w-full px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all min-h-[100px] resize-none"
                    placeholder="例如：建立一个可持续发展的个人生态系统..."
                    value={formData.vision}
                    onChange={(e) => setFormData({ ...formData, vision: e.target.value })}
                  />
                </div>

                <div className="space-y-3">
                  <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">当前具体目标</label>
                  <div className="space-y-3">
                    {formData.goals.map((goal: string, index: number) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="text"
                          className="flex-1 px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all"
                          placeholder={`目标 ${index + 1}`}
                          value={goal}
                          onChange={(e) => {
                            const newGoals = [...formData.goals];
                            newGoals[index] = e.target.value;
                            setFormData({ ...formData, goals: newGoals });
                          }}
                        />
                        {formData.goals.length > 1 && (
                          <button 
                            onClick={() => setFormData({ ...formData, goals: formData.goals.filter((_: string, i: number) => i !== index) })}
                            className="p-4 rounded-2xl hover:bg-[var(--md-sys-color-error-container)] hover:text-[var(--md-sys-color-on-error-container)] transition-colors opacity-30 hover:opacity-100"
                          >
                            <X size={20} />
                          </button>
                        )}
                      </div>
                    ))}
                    <button 
                      onClick={() => setFormData({ ...formData, goals: [...formData.goals, ''] })}
                      className="flex items-center gap-2 text-sm font-bold opacity-50 hover:opacity-100 px-2 py-1 transition-all"
                    >
                      <Plus size={16} /> 添加目标
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 底部按钮 */}
          <div className="flex justify-between items-center mt-12 pt-8 border-t border-[var(--md-sys-color-outline-variant)]">
            <button
              onClick={() => step > 1 && setStep(step - 1)}
              disabled={step === 1}
              className={clsx(
                "flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all",
                step === 1 ? "opacity-0 pointer-events-none" : "opacity-50 hover:opacity-100"
              )}
            >
              <ArrowLeft size={20} /> 返回
            </button>
            
            <Button
              onClick={handleNext}
              className="px-10 py-6 rounded-2xl shadow-xl shadow-[var(--md-sys-color-primary)]/20 font-black tracking-tighter"
            >
              {step === totalSteps ? (mode === 'settings' ? '保存设置' : '开启系统') : '继续下一步'}
              <ArrowRight size={20} className="ml-2" />
            </Button>
          </div>
        </GlassCard>
      </main>
    </div>
  );
}

