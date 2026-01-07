/**
 * 毛玻璃卡片组件
 */
import clsx from 'clsx';
import { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export default function GlassCard({
  children,
  className,
  hover = false,
  padding = 'md',
}: GlassCardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  return (
    <div
      className={clsx(
        'rounded-2xl',
        'bg-[var(--glass-bg)]',
        'backdrop-blur-[12px]',
        'border border-[var(--glass-border)]',
        paddingClasses[padding],
        hover && 'transition-all duration-200 hover:border-[var(--color-primary-alpha-40)] hover:shadow-[var(--shadow-glow)]',
        className
      )}
    >
      {children}
    </div>
  );
}

