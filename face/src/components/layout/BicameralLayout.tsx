import { useState, type ReactNode } from 'react';
import CortexBar from './CortexBar';
import clsx from 'clsx';

interface BicameralLayoutProps {
  brainView: ReactNode;
  screenView: ReactNode;
}

/**
 * 双室布局 (Bicameral Layout)
 * 实现 “一脑 (Brain/Chat)” 与 “一屏 (Screen/Dashboard)” 的极简切换
 */
export default function BicameralLayout({ brainView, screenView }: BicameralLayoutProps) {
  const [activeView, setActiveView] = useState<'brain' | 'screen'>('screen');

  return (
    <div className="min-h-screen bg-[var(--md-sys-color-surface)] text-[var(--md-sys-color-on-surface)] transition-colors duration-500">
      {/* 顶部导航栏 */}
      <CortexBar 
        activeView={activeView} 
        onViewChange={setActiveView} 
      />

      {/* 视图容器 */}
      <main className="relative h-screen overflow-hidden">
        {/* 一脑视图 (Chat) */}
        <div 
          className={clsx(
            "absolute inset-0 pt-16 transition-all duration-700 ease-in-out",
            activeView === 'brain' 
              ? "opacity-100 translate-y-0 pointer-events-auto" 
              : "opacity-0 -translate-y-12 pointer-events-none"
          )}
        >
          {brainView}
        </div>

        {/* 一屏视图 (Dashboard/Screen) */}
        <div 
          className={clsx(
            "absolute inset-0 pt-16 transition-all duration-700 ease-in-out overflow-y-auto",
            activeView === 'screen' 
              ? "opacity-100 translate-y-0 pointer-events-auto" 
              : "opacity-0 translate-y-12 pointer-events-none"
          )}
        >
          {screenView}
        </div>
      </main>
    </div>
  );
}
