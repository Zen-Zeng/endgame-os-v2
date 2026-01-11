/**
 * Endgame OS v2 - Sidebar (Navigation Drawer)
 * Strictly following M3 Navigation Rail/Drawer specs
 */
import { useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  LayoutDashboard, 
  MessageSquare, 
  Target, 
  Settings, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Activity,
  UserCircle,
  Share2,
  Brain,
  X,
  Sparkles,
  User,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useUIStore } from '../../stores/useUIStore';
import { useH3Store } from '../../stores/useH3Store';
import { api } from '../../lib/api';
import Button from '../ui/Button';
import clsx from 'clsx';

function H3EnergyDisplay() {
  const { scores } = useH3Store();
  
  const items = [
    { label: 'Mind', value: scores.mind, color: 'bg-blue-500' },
    { label: 'Body', value: scores.body, color: 'bg-green-500' },
    { label: 'Spirit', value: scores.spirit, color: 'bg-purple-500' },
    { label: 'Vocation', value: scores.vocation, color: 'bg-amber-500' },
  ];

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="space-y-1">
          <div className="flex justify-between text-[10px] font-medium text-[var(--md-sys-color-on-surface-variant)]">
            <span>{item.label}</span>
            <span>{item.value}%</span>
          </div>
          <div className="h-1.5 w-full bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden">
            <div 
              className={clsx("h-full rounded-full transition-all duration-500", item.color)} 
              style={{ width: `${item.value}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// 设置弹窗组件
interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

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

function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
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

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const userData = await api.get<any>('/auth/me');
      if (userData) {
        setProfile({
          name: userData.name || '',
          email: userData.email || '',
        });
        if (userData.vision) {
          setVision({
            title: userData.vision.title || '',
            description: userData.vision.description || '',
            core_values: userData.vision.core_values || [],
            key_milestones: userData.vision.key_milestones || [],
          });
        }
      }

      const personaData = await api.get<any>('/persona/current');
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
    } finally {
      setIsLoading(false);
    }
  };

  const handleSavePersona = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');
      await api.put('/persona/current', personaConfig);
      setSaveStatus('success');
    } catch (error) {
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveVision = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');
      await api.patch('/auth/me', { vision });
      setSaveStatus('success');
    } catch (error) {
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveProfile = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('idle');
      await api.patch('/auth/me', { name: profile.name });
      setSaveStatus('success');
    } catch (error) {
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  const tabs = [
    { id: 'persona', label: '数字人格', icon: Sparkles },
    { id: 'vision', label: '终局愿景', icon: Target },
    { id: 'profile', label: '个人信息', icon: User },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[var(--md-sys-color-surface-container)] w-full max-w-3xl h-[65vh] rounded-[var(--md-sys-shape-corner-extra-large)] shadow-2xl flex overflow-hidden animate-in zoom-in-95 duration-200">
        {/* 弹窗左侧栏 */}
        <div className="w-64 bg-[var(--md-sys-color-surface-container-low)] border-r border-[var(--md-sys-color-outline-variant)] flex flex-col p-4">
          <button 
            onClick={onClose}
            className="mb-8 p-2 w-fit rounded-full hover:bg-[var(--md-sys-color-surface-container-highest)] transition-colors"
          >
            <X size={20} className="text-[var(--md-sys-color-on-surface-variant)]" />
          </button>
          
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id as any);
                  setSaveStatus('idle');
                }}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-[var(--md-sys-shape-corner-full)] transition-all font-medium text-sm",
                  activeTab === tab.id
                    ? "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)]"
                    : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)]"
                )}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* 弹窗右侧主内容区 */}
        <div className="flex-1 flex flex-col bg-[var(--md-sys-color-surface)] overflow-y-auto">
          <header className="px-8 py-6 border-b border-[var(--md-sys-color-outline-variant)]">
            <h2 className="text-2xl font-bold text-[var(--md-sys-color-on-surface)]">
              {tabs.find(t => t.id === activeTab)?.label}
            </h2>
            <p className="text-sm text-[var(--md-sys-color-on-surface-variant)] mt-1">
              管理你的系统配置与个人偏好
            </p>
          </header>

          <div className="flex-1 p-8">
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-[var(--md-sys-color-primary)]" />
              </div>
            ) : (
              <div className="max-w-2xl space-y-8 animate-in slide-in-from-bottom-2 duration-300">
                {saveStatus !== 'idle' && (
                  <div className={clsx(
                    "p-4 rounded-xl flex items-center gap-3",
                    saveStatus === 'success' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
                  )}>
                    {saveStatus === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                    <span className="text-sm font-medium">
                      {saveStatus === 'success' ? '保存成功' : '保存失败，请重试'}
                    </span>
                  </div>
                )}

                {activeTab === 'persona' && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">AI 名称</label>
                      <input 
                        type="text" 
                        value={personaConfig.name}
                        onChange={e => setPersonaConfig({...personaConfig, name: e.target.value})}
                        className="w-full bg-[var(--md-sys-color-surface-container-high)] border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">交互语气</label>
                      <select 
                        value={personaConfig.tone}
                        onChange={e => setPersonaConfig({...personaConfig, tone: e.target.value as any})}
                        className="w-full bg-[var(--md-sys-color-surface-container-high)] border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none"
                      >
                        <option value="mentor">导师 (Mentor)</option>
                        <option value="coach">教练 (Coach)</option>
                        <option value="partner">伙伴 (Partner)</option>
                        <option value="analyst">分析师 (Analyst)</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">主动性等级: {personaConfig.proactive_level}</label>
                      <input 
                        type="range" min="1" max="5" 
                        value={personaConfig.proactive_level}
                        onChange={e => setPersonaConfig({...personaConfig, proactive_level: parseInt(e.target.value)})}
                        className="w-full accent-[var(--md-sys-color-primary)]"
                      />
                    </div>
                    <div className="flex items-center gap-3 p-4 rounded-xl bg-[var(--md-sys-color-surface-container-low)]">
                      <input 
                        type="checkbox" 
                        checked={personaConfig.challenge_mode}
                        onChange={e => setPersonaConfig({...personaConfig, challenge_mode: e.target.checked})}
                        className="w-5 h-5 rounded border-none accent-[var(--md-sys-color-primary)]"
                      />
                      <span className="text-sm font-medium">启用挑战模式</span>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">人格指令 (System Prompt)</label>
                      <textarea 
                        value={personaConfig.system_prompt_template}
                        onChange={e => setPersonaConfig({...personaConfig, system_prompt_template: e.target.value})}
                        placeholder="输入 AI 的核心指令、行为准则或特定的语气要求..."
                        className="w-full h-32 bg-[var(--md-sys-color-surface-container-high)] border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none resize-none text-sm"
                      />
                    </div>
                    <Button onClick={handleSavePersona} loading={isSaving} className="w-full">
                      保存人格配置
                    </Button>
                  </div>
                )}

                {activeTab === 'vision' && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">愿景标题</label>
                      <input 
                        type="text" 
                        value={vision.title}
                        onChange={e => setVision({...vision, title: e.target.value})}
                        className="w-full bg-[var(--md-sys-color-surface-container-high)] border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none"
                        placeholder="例如: 成为自由职业者"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">详细描述</label>
                      <textarea 
                        value={vision.description}
                        onChange={e => setVision({...vision, description: e.target.value})}
                        className="w-full h-40 bg-[var(--md-sys-color-surface-container-high)] border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none resize-none"
                      />
                    </div>
                    <Button onClick={handleSaveVision} loading={isSaving} className="w-full">
                      保存愿景配置
                    </Button>
                  </div>
                )}

                {activeTab === 'profile' && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">显示名称</label>
                      <input 
                        type="text" 
                        value={profile.name}
                        onChange={e => setProfile({...profile, name: e.target.value})}
                        className="w-full bg-[var(--md-sys-color-surface-container-high)] border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-[var(--md-sys-color-primary)] outline-none"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">电子邮箱</label>
                      <input 
                        type="email" 
                        value={profile.email}
                        disabled
                        className="w-full bg-[var(--md-sys-color-surface-container-low)] border-none rounded-xl px-4 py-3 opacity-60 cursor-not-allowed outline-none"
                      />
                    </div>
                    <Button onClick={handleSaveProfile} loading={isSaving} className="w-full">
                      更新个人信息
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const menuGroups = [
  {
    label: '核心',
    items: [
      { id: 'dashboard', icon: LayoutDashboard, label: '概览', path: '/' },
      { id: 'chat', icon: MessageSquare, label: '对话', path: '/chat' },
      { id: 'calibration', icon: Activity, label: '校准', path: '/calibration' },
      { id: 'goals', icon: Target, label: '目标', path: '/goals' },
    ]
  },
  {
    label: '心智',
    items: [
      { id: 'neural', icon: Share2, label: '神经链接', path: '/neural-link' },
      { id: 'memory', icon: Brain, label: '记忆图谱', path: '/memory-map' },
    ]
  }
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const userInitial = user?.name ? user.name.charAt(0).toUpperCase() : 'E';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <>
      <aside 
        className={clsx(
          "sidebar flex flex-col transition-all duration-400 ease-in-out",
          sidebarCollapsed && "w-[80px]"
        )}
        style={{ '--current-sidebar-width': sidebarCollapsed ? '80px' : '280px' } as any}
      >
        {/* 1. LOGO AREA / AVATAR SETTINGS */}
        <div className="h-20 flex items-center px-6 mb-6 relative">
          <div 
            onClick={() => setIsSettingsOpen(true)}
            className="w-10 h-10 rounded-xl bg-[var(--md-sys-color-primary)] flex items-center justify-center text-[var(--md-sys-color-on-primary)] shadow-lg cursor-pointer hover:scale-110 active:scale-95 transition-all group relative shrink-0"
          >
            <span className="text-xl font-black">{userInitial}</span>
            <div className="absolute -right-1 -bottom-1 w-4 h-4 bg-[var(--md-sys-color-surface-container-highest)] rounded-full flex items-center justify-center border border-[var(--md-sys-color-outline-variant)] opacity-0 group-hover:opacity-100 transition-opacity">
              <Settings size={10} className="text-[var(--md-sys-color-on-surface-variant)]" />
            </div>
          </div>
          
          {!sidebarCollapsed && (
            <span className="ml-4 text-xl font-black tracking-tighter text-[var(--md-sys-color-on-surface)] truncate flex-1">
              ENDGAME <span className="text-[var(--md-sys-color-primary)]">OS</span>
            </span>
          )}

          <button
             onClick={toggleSidebar}
             className="absolute top-6 right-2 w-8 h-8 rounded-full flex items-center justify-center hover:bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] transition-all z-10"
           >
             {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
           </button>
        </div>

        {/* 2. NAVIGATION ITEMS */}
        <nav className="flex-1 px-3 space-y-6 overflow-y-auto scrollbar-hide">
          {menuGroups.map((group) => (
            <div key={group.label} className="space-y-1">
              {!sidebarCollapsed && (
                <p className="px-4 text-[var(--md-sys-typescale-label-small-size)] font-bold text-[var(--md-sys-color-on-surface-variant)] opacity-50 uppercase tracking-widest mb-2">
                  {group.label}
                </p>
              )}
              {group.items.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <button
                    key={item.id}
                    onClick={() => navigate(item.path)}
                    className={clsx(
                      "w-full flex items-center h-12 px-4 rounded-[var(--md-sys-shape-corner-full)] transition-all relative group",
                      isActive 
                        ? "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)]" 
                        : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)]"
                    )}
                  >
                    <item.icon 
                      size={22} 
                      className={clsx(
                        "transition-transform group-active:scale-90",
                        isActive ? "stroke-[2.5px]" : "stroke-[2px]"
                      )} 
                    />
                    {!sidebarCollapsed && (
                      <span className={clsx(
                        "ml-4 font-bold text-sm tracking-wide",
                        isActive ? "opacity-100" : "opacity-70"
                      )}>
                        {item.label}
                      </span>
                    )}
                    {isActive && sidebarCollapsed && (
                      <div className="absolute left-0 w-1 h-6 bg-[var(--md-sys-color-primary)] rounded-r-full" />
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* H3 Energy Status */}
        {!sidebarCollapsed && (
          <div className="px-6 py-4 mb-2">
            <p className="text-[10px] font-bold text-[var(--md-sys-color-on-surface-variant)] opacity-50 uppercase tracking-widest mb-3">
              Energy State
            </p>
            <H3EnergyDisplay />
          </div>
        )}

        {/* 3. FOOTER */}
        <div className="p-4 space-y-2">
          <button
            onClick={handleLogout}
            className={clsx(
              "w-full flex items-center h-12 px-4 rounded-full text-[var(--md-sys-color-error)] hover:bg-[var(--md-sys-color-error-container)] hover:bg-opacity-10 transition-colors",
              sidebarCollapsed ? "justify-center" : "gap-4"
            )}
          >
            <LogOut size={20} />
            {!sidebarCollapsed && <span className="text-sm font-bold">退出系统</span>}
          </button>
        </div>
      </aside>

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </>
  );
}
