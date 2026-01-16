import { Brain, LayoutDashboard, Settings, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import SettingsModal from '../SettingsModal';
import clsx from 'clsx';

interface CortexBarProps {
  activeView: 'brain' | 'screen';
  onViewChange: (view: 'brain' | 'screen') => void;
}

export default function CortexBar({ activeView, onViewChange }: CortexBarProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <>
      <header className="fixed top-0 left-0 right-0 h-16 bg-[var(--md-sys-color-surface)]/80 backdrop-blur-xl border-b border-[var(--md-sys-color-outline-variant)] z-50 flex items-center justify-between px-6">
        {/* 系统标识 */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[var(--md-sys-color-primary)] rounded-lg flex items-center justify-center text-[var(--md-sys-color-on-primary)] font-black cursor-pointer hover:scale-110 transition-transform" onClick={() => navigate('/')}>
            E
          </div>
          <span className="text-sm font-black uppercase tracking-[0.2em] hidden sm:block">Endgame OS</span>
        </div>

        {/* 核心相位切换器 (Phase Switcher) */}
        <div className="flex bg-[var(--md-sys-color-surface-container-high)] p-1 rounded-full shadow-inner border border-[var(--md-sys-color-outline-variant)]">
          <button
            onClick={() => onViewChange('screen')}
            className={clsx(
              "flex items-center gap-2 px-6 py-1.5 rounded-full text-xs font-black transition-all duration-300",
              activeView === 'screen' 
                ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-md scale-105" 
                : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
            )}
          >
            <LayoutDashboard size={14} />
            一屏 / SCREEN
          </button>
          <button
            onClick={() => onViewChange('brain')}
            className={clsx(
              "flex items-center gap-2 px-6 py-1.5 rounded-full text-xs font-black transition-all duration-300",
              activeView === 'brain' 
                ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-md scale-105" 
                : "text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-variant)]"
            )}
          >
            <Brain size={14} />
            一脑 / BRAIN
          </button>
        </div>

        {/* 用户与设置 */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-xs font-black">{user?.name || '岳'}</span>
            <span className="text-[10px] text-[var(--md-sys-color-primary)] font-bold uppercase">System Operator</span>
          </div>
          
          <button 
            onClick={() => setIsSettingsOpen(true)}
            className="w-10 h-10 rounded-full bg-[var(--md-sys-color-primary)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-center overflow-hidden hover:opacity-80 transition-all text-[var(--md-sys-color-on-primary)] font-black"
          >
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <span className="text-lg">岳</span>
            )}
          </button>
        </div>
      </header>

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </>
  );
}

