/**
 * Endgame OS v2 - M3 Card Component
 * Strictly following M3 Surface Container Roles
 */
import clsx from 'clsx';
import type { ReactNode, CSSProperties } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
  style?: CSSProperties;
  /**
   * M3 标准变体:
   * elevated: 适用于需要从背景中突出的主内容
   * filled: 适用于次要内容，与背景有轻微色差
   * outlined: 适用于并列的列表项或弱引导内容
   */
  variant?: 'elevated' | 'filled' | 'outlined' | 'none';
  /**
   * M3 标准内边距:
   * none: 0
   * sm: 16px (用于小列表项)
   * md: 24px (标准间距，M3 Content Gap)
   * lg: 32px (大容器间距)
   */
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export default function GlassCard({
  children,
  className,
  hover = false,
  variant = 'filled',
  padding = 'md',
  onClick,
  style,
}: GlassCardProps) {
  const variantClasses = {
    none: 'bg-transparent',
    elevated: 'bg-[var(--md-sys-color-surface-container-low)] shadow-md border-none',
    filled: 'bg-[var(--md-sys-color-surface-container)] border-none',
    outlined: 'bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)]',
  };

  const paddingClasses = {
    none: 'p-0',
    sm: 'p-[var(--md-sys-spacing-2)]', // 16px
    md: 'p-[var(--md-sys-spacing-3)]', // 24px - M3 推荐的标准间距
    lg: 'p-[var(--md-sys-spacing-4)]', // 32px
  };

  return (
    <div
      onClick={onClick}
      style={style}
      className={clsx(
        /* M3 标准大圆角 (28dp) */
        'rounded-[var(--md-sys-shape-corner-extra-large)] transition-all duration-300 ease-out',
        variantClasses[variant],
        paddingClasses[padding],
        hover && 'hover:bg-[var(--md-sys-color-surface-container-high)] hover:translate-y-[-2px] cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  );
}
