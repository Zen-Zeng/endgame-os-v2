/**
 * Endgame OS v2 - M3 Button Component
 * Supporting 5 standard M3 button types
 */
import type { ReactNode, ButtonHTMLAttributes } from 'react';
import clsx from 'clsx';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'filled' | 'elevated' | 'tonal' | 'outlined' | 'text';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: ReactNode;
  loading?: boolean;
  fullWidth?: boolean;
}

export default function Button({
  children,
  variant = 'filled',
  icon,
  loading = false,
  fullWidth = false,
  className,
  disabled,
  ...props
}: ButtonProps) {
  
  const baseClasses = "relative flex items-center justify-center gap-2 px-6 h-12 rounded-[var(--md-sys-shape-corner-full)] font-bold text-sm tracking-wide transition-all duration-200 active:scale-[0.97] disabled:opacity-40 disabled:pointer-events-none overflow-hidden group";
  
  const variantClasses = {
    filled: "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-md hover:shadow-lg shadow-[var(--md-sys-color-primary)]/20",
    elevated: "bg-[var(--md-sys-color-surface-container-low)] text-[var(--md-sys-color-primary)] shadow-md hover:shadow-lg hover:bg-[var(--md-sys-color-surface-container-high)]",
    tonal: "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] hover:bg-[var(--md-sys-color-secondary-container)]/80",
    outlined: "bg-transparent border border-[var(--md-sys-color-outline)] text-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-primary)]/5",
    text: "bg-transparent text-[var(--md-sys-color-primary)] px-3 hover:bg-[var(--md-sys-color-primary)]/10",
  };

  return (
    <button
      className={clsx(
        baseClasses,
        variantClasses[variant],
        fullWidth && "w-full",
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {/* Ripple Effect Placeholder (M3 standard requires ripple, but we use scale/bg for now) */}
      {loading ? (
        <Loader2 className="animate-spin" size={18} />
      ) : (
        icon && <span className="transition-transform group-hover:scale-110">{icon}</span>
      )}
      <span className={clsx(loading && "opacity-70")}>{children}</span>
    </button>
  );
}
