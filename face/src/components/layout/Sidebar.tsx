/**
 * 侧边栏组件
 */
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  Activity,
  FolderOpen,
  Network,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import clsx from 'clsx';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: '仪表盘' },
  { to: '/chat', icon: MessageSquare, label: '对话' },
  { to: '/calibration', icon: Activity, label: 'H3 校准' },
  { to: '/archives', icon: FolderOpen, label: '档案库' },
  { to: '/memory', icon: Network, label: '记忆图谱' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuthStore();

  // 更新 CSS 变量以反映侧边栏状态
  useEffect(() => {
    const root = document.documentElement;
    if (collapsed) {
      root.style.setProperty('--current-sidebar-width', 'var(--sidebar-collapsed-width, 72px)');
      document.body.classList.add('sidebar-collapsed');
    } else {
      root.style.setProperty('--current-sidebar-width', 'var(--sidebar-width, 280px)');
      document.body.classList.remove('sidebar-collapsed');
    }
  }, [collapsed]);

  return (
    <aside
      className={clsx(
        'sidebar',
        'fixed left-0 top-0 h-full z-50',
        'flex flex-col',
        'bg-[var(--color-bg-card)] border-r border-[var(--color-border)]',
        'transition-all duration-300'
      )}
      style={{
        width: collapsed ? 'var(--sidebar-collapsed-width, 72px)' : 'var(--sidebar-width, 280px)',
      }}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-primary)] flex items-center justify-center">
            <span className="text-white font-bold text-lg">E</span>
          </div>
          {!collapsed && (
            <div className="animate-fade-in">
              <h1 className="font-display text-lg font-semibold text-[var(--color-text-primary)]">
                Endgame OS
              </h1>
              <p className="text-xs text-[var(--color-text-muted)]">v2.0</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.to;
          
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={clsx(
                'flex items-center gap-3 px-3 py-3 rounded-xl',
                'transition-all duration-200',
                'group',
                isActive
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card-hover)] hover:text-[var(--color-text-primary)]'
              )}
            >
              <Icon
                size={20}
                className={clsx(
                  'flex-shrink-0',
                  isActive ? 'text-white' : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-primary)]'
                )}
              />
              {!collapsed && (
                <span className="font-medium text-sm animate-fade-in">
                  {item.label}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 border-t border-[var(--color-border)] space-y-2">
        {/* User */}
        {user && (
          <div
            className={clsx(
              'flex items-center gap-3 px-3 py-2 rounded-xl',
              'bg-[var(--color-bg-elevated)]'
            )}
          >
            <div className="w-8 h-8 rounded-full bg-[var(--color-primary-alpha-20)] flex items-center justify-center">
              <span className="text-[var(--color-primary)] text-sm font-medium">
                {user.name.charAt(0).toUpperCase()}
              </span>
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0 animate-fade-in">
                <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                  {user.name}
                </p>
                <p className="text-xs text-[var(--color-text-muted)] truncate">
                  {user.email}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Settings & Logout */}
        <div className="flex gap-2">
          <NavLink
            to="/settings"
            className={clsx(
              'flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl',
              'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card-hover)]',
              'transition-all duration-200'
            )}
          >
            <Settings size={18} />
            {!collapsed && <span className="text-sm">设置</span>}
          </NavLink>
          <button
            onClick={logout}
            className={clsx(
              'flex items-center justify-center px-3 py-2 rounded-xl',
              'text-[var(--color-text-secondary)] hover:bg-[var(--color-error)] hover:text-white',
              'transition-all duration-200'
            )}
          >
            <LogOut size={18} />
          </button>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={clsx(
            'w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl',
            'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-card-hover)]',
            'transition-all duration-200'
          )}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!collapsed && <span className="text-sm">收起</span>}
        </button>
      </div>
    </aside>
  );
}

