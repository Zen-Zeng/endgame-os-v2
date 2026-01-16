import React, { useState } from 'react';
import { 
  X, 
  Settings, 
  User, 
  Brain, 
  Target, 
  RefreshCw, 
  LogOut,
  ChevronRight,
  Shield,
  Palette,
  Bell
} from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';
import { useOnboardingStore } from '../stores/useOnboardingStore';
import { api } from '../lib/api';
import Button from './ui/Button';
import clsx from 'clsx';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type SettingsSection = 'profile' | 'persona' | 'vision' | 'system';

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { user, logout } = useAuthStore();
  const { resetOnboarding } = useOnboardingStore();
  const [activeSection, setActiveSection] = useState<SettingsSection>('profile');
  const [isResetting, setIsResetting] = useState(false);
  const [selectedClearItems, setSelectedClearItems] = useState<string[]>(['onboarding', 'chat', 'h3', 'files', 'memory']);

  // 新增：归一化愿景与目标数据
  const [normalizedVision, setNormalizedVision] = useState<{title: string, description: string} | null>(null);
  const [normalizedGoals, setNormalizedGoals] = useState<any[]>([]);
  const [loadingNormalized, setLoadingNormalized] = useState(false);

  React.useEffect(() => {
    if (isOpen && activeSection === 'vision') {
      fetchNormalizedData();
    }
  }, [isOpen, activeSection]);

  const fetchNormalizedData = async () => {
    try {
      setLoadingNormalized(true);
      const vision = await api.get<any>('/goals/vision');
      const goals = await api.get<any[]>('/goals/list');
      if (vision) setNormalizedVision({ title: vision.title, description: vision.description });
      if (goals) setNormalizedGoals(goals);
    } catch (e) {
      console.error('Fetch normalized vision data error', e);
    } finally {
      setLoadingNormalized(false);
    }
  };

  if (!isOpen) return null;

  const clearableItems = [
    { id: 'onboarding', label: '引导状态与人格设定', desc: '清除你的人格设定、愿景目标和引导进度' },
    { id: 'chat', label: '对话历史数据', desc: '清除所有与 AI 的聊天记录和消息详情' },
    { id: 'h3', label: 'H3 能量校准记录', desc: '清除所有的能量监测历史和校准记录' },
    { id: 'files', label: '上传的原始文件', desc: '删除所有已上传到系统的文档和资料' },
    { id: 'memory', label: '提取的知识图谱', desc: '清除从对话和文件中自动提取的知识节点与关系' },
  ];

  const toggleClearItem = (id: string) => {
    setSelectedClearItems(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSystemReset = async () => {
    if (selectedClearItems.length === 0) {
      alert('请至少选择一个要清除的数据项');
      return;
    }

    if (!window.confirm(`确定要清除选中的 ${selectedClearItems.length} 项数据吗？此操作不可撤销。`)) {
      return;
    }

    setIsResetting(true);
    try {
      // 调用后端重置接口
      await api.post('/auth/reset', { items: selectedClearItems });
      
      // 如果清除了引导状态，则需要重新登录或跳转
      if (selectedClearItems.includes('onboarding')) {
        resetOnboarding();
        logout();
        window.location.href = '/login';
      } else {
        alert('选中的数据已成功清除');
        onClose();
      }
    } catch (error) {
      console.error('重置失败:', error);
      alert('数据清除失败，请重试');
    } finally {
      setIsResetting(false);
    }
  };

  const sections = [
    { id: 'profile', label: '个人信息', icon: <User size={18} /> },
    { id: 'persona', label: '数字人格', icon: <Brain size={18} /> },
    { id: 'vision', label: '终局愿景', icon: <Target size={18} /> },
    { id: 'system', label: '系统安全', icon: <Shield size={18} /> },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 md:p-10">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative w-full max-w-5xl h-full max-h-[700px] bg-[var(--md-sys-color-surface)] rounded-[32px] shadow-2xl border border-[var(--md-sys-color-outline-variant)] overflow-hidden flex flex-col md:flex-row">
        
        {/* Sidebar */}
        <div className="w-full md:w-64 bg-[var(--md-sys-color-surface-container-low)] border-r border-[var(--md-sys-color-outline-variant)] flex flex-col">
          <div className="p-6">
            <h2 className="text-xl font-black flex items-center gap-2">
              <Settings size={22} className="text-[var(--md-sys-color-primary)]" />
              系统设置
            </h2>
          </div>
          
          <nav className="flex-1 px-3 space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id as SettingsSection)}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold transition-all",
                  activeSection === section.id 
                    ? "bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] shadow-sm" 
                    : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
                )}
              >
                {section.icon}
                {section.label}
              </button>
            ))}
          </nav>
          
          <div className="p-4 border-t border-[var(--md-sys-color-outline-variant)]">
            <button 
              onClick={logout}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-bold text-red-500 hover:bg-red-50 transition-colors"
            >
              <LogOut size={18} />
              退出登录
            </button>
          </div>
        </div>
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-[var(--md-sys-color-outline-variant)]">
            <h3 className="text-lg font-black">
              {sections.find(s => s.id === activeSection)?.label}
            </h3>
            <button 
              onClick={onClose}
              className="p-2 rounded-full hover:bg-[var(--md-sys-color-surface-variant)] transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          
          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
            {activeSection === 'profile' && (
              <div className="space-y-8 animate-fade-in">
                <div className="flex items-center gap-6">
                  <div className="w-20 h-20 rounded-full bg-[var(--md-sys-color-primary)] flex items-center justify-center text-3xl font-black text-[var(--md-sys-color-on-primary)] shadow-lg">
                    {user?.name?.[0] || '岳'}
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xl font-bold">{user?.name}</h4>
                    <p className="text-sm text-[var(--md-sys-color-on-surface-variant)]">{user?.email}</p>
                  </div>
                </div>
                
                <div className="grid gap-6 max-w-md">
                  <div className="space-y-2">
                    <label className="text-xs font-bold uppercase tracking-widest opacity-50 ml-1">用户姓名</label>
                    <input 
                      type="text" 
                      defaultValue={user?.name}
                      className="w-full px-5 py-3 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all"
                    />
                  </div>
                </div>
              </div>
            )}
            
            {activeSection === 'persona' && (
              <div className="space-y-6 animate-fade-in">
                <div className="p-6 rounded-3xl bg-[var(--md-sys-color-primary-container)]/30 border border-[var(--md-sys-color-primary)]/20">
                  <h4 className="font-bold mb-2 flex items-center gap-2">
                    <Brain size={18} />
                    {user?.persona?.name || 'The Architect'}
                  </h4>
                  <p className="text-sm opacity-70 leading-relaxed">
                    当前采用 {user?.persona?.tone || '导师'} 风格。系统将以严谨且富有洞察力的方式与你互动。
                  </p>
                </div>
                
                <div className="grid gap-4">
                  <Button variant="outlined" className="justify-start h-14 rounded-2xl">
                    <Palette size={18} className="mr-2" />
                    修改交互性格
                    <ChevronRight size={16} className="ml-auto opacity-30" />
                  </Button>
                  <Button variant="outlined" className="justify-start h-14 rounded-2xl">
                    <Bell size={18} className="mr-2" />
                    主动性偏好设置
                    <ChevronRight size={16} className="ml-auto opacity-30" />
                  </Button>
                </div>
              </div>
            )}
            
            {activeSection === 'vision' && (
              <div className="space-y-6 animate-fade-in">
                {loadingNormalized ? (
                  <div className="flex items-center justify-center py-12 gap-3 opacity-50">
                    <RefreshCw size={20} className="animate-spin" />
                    <span className="text-sm font-bold">同步全系统目标数据...</span>
                  </div>
                ) : (
                  <>
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-widest opacity-50 ml-1">当前愿景</label>
                      <div className="p-6 rounded-3xl bg-[var(--md-sys-color-surface-container-highest)] min-h-[120px] text-sm leading-relaxed">
                        {normalizedVision?.description || user?.vision?.description || '尚未设定愿景'}
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between items-center ml-1">
                        <label className="text-xs font-bold uppercase tracking-widest opacity-50">全系统归一化目标</label>
                        <span className="text-[10px] font-black bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] px-2 py-0.5 rounded-full">SSOT</span>
                      </div>
                      <div className="space-y-2">
                        {normalizedGoals.length > 0 ? (
                          normalizedGoals.map((goal, i) => (
                            <div key={goal.id || i} className="flex items-center justify-between px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-low)] border border-[var(--md-sys-color-outline-variant)]">
                              <div className="flex items-center gap-3 text-sm">
                                <div className="w-2 h-2 rounded-full bg-[var(--md-sys-color-primary)]" />
                                <span className="font-bold">{goal.name}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-black opacity-40 uppercase">{goal.dossier?.status || 'active'}</span>
                                <div className="w-12 h-1 bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden">
                                  <div className="h-full bg-[var(--md-sys-color-primary)]" style={{ width: `${goal.dossier?.progress || 0}%` }} />
                                </div>
                              </div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm opacity-40 italic p-4 text-center">暂无目标数据</p>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
            
            {activeSection === 'system' && (
              <div className="space-y-8 animate-fade-in">
                <div className="p-6 rounded-3xl border border-red-200 bg-red-50/50 space-y-6">
                  <div>
                    <h4 className="font-black text-red-600 flex items-center gap-2">
                      <RefreshCw size={18} />
                      数据清除与重置 / Data Clearing
                    </h4>
                    <p className="text-sm text-red-500/70 mt-1">
                      请选择你想要从系统中清除的数据类型。此操作将永久删除相关历史记录。
                    </p>
                  </div>
                  
                  <div className="grid gap-3">
                    {clearableItems.map(item => (
                      <div 
                        key={item.id}
                        onClick={() => toggleClearItem(item.id)}
                        className={clsx(
                          "flex items-start gap-4 p-4 rounded-2xl border transition-all cursor-pointer",
                          selectedClearItems.includes(item.id)
                            ? "bg-red-100 border-red-200"
                            : "bg-white/50 border-gray-100 hover:border-red-100"
                        )}
                      >
                        <div className={clsx(
                          "mt-1 w-5 h-5 rounded border flex items-center justify-center transition-all",
                          selectedClearItems.includes(item.id)
                            ? "bg-red-500 border-red-500 text-white"
                            : "bg-white border-gray-300"
                        )}>
                          {selectedClearItems.includes(item.id) && <X size={14} strokeWidth={4} />}
                        </div>
                        <div className="space-y-1">
                          <div className={clsx(
                            "text-sm font-bold",
                            selectedClearItems.includes(item.id) ? "text-red-700" : "text-gray-700"
                          )}>
                            {item.label}
                          </div>
                          <div className="text-xs text-gray-500 leading-relaxed">
                            {item.desc}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <div className="pt-2">
                    <Button 
                      onClick={handleSystemReset}
                      loading={isResetting}
                      disabled={selectedClearItems.length === 0}
                      className="w-full bg-red-500 hover:bg-red-600 text-white border-none shadow-red-200 h-12 rounded-2xl"
                    >
                      确认清除选中的数据
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Footer */}
          <div className="p-6 border-t border-[var(--md-sys-color-outline-variant)] flex justify-end gap-3">
            <Button variant="text" onClick={onClose}>取消</Button>
            <Button onClick={onClose}>保存更改</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
