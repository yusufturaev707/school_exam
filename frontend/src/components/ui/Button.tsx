import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { Spinner } from './Spinner';

/*
 * Dizayn: Button (bd-btn). Asosiy — 48px, 3D pastki qirra (--shadow-press), bosilganda qirra 3px tushadi.
 * Ikkinchi darajali — 40px, brand-soft. Hit-area har doim ≥ 44px (::after).
 */
type Variant = 'primary' | 'secondary' | 'ghost' | 'light' | 'danger';
type Size = 'md' | 'lg';

const variants: Record<Variant, string> = {
  primary: 'bd-btn--primary',
  secondary: 'bd-btn--secondary',
  ghost: 'bd-btn--ghost',
  light: 'bd-btn--light',
  danger: 'bd-btn--danger',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** `lg` — 48px (asosiy amal). Asosiy/light/danger har doim 48px. */
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

/** Link (`<a>`/`<Link>`) uchun bir xil koʻrinish: `className={buttonClass('primary')}` */
export function buttonClass(variant: Variant = 'primary', opts: { size?: Size; fullWidth?: boolean; className?: string } = {}) {
  return cn('bd-btn', variants[variant], opts.size === 'lg' && variant !== 'primary' && 'h-[var(--control-lg)]', opts.fullWidth && 'bd-btn--block', opts.className);
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, fullWidth, leftIcon, rightIcon, className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, { size, fullWidth, className })}
      {...rest}
    >
      {loading ? <Spinner className="size-5" /> : leftIcon}
      <span>{children}</span>
      {!loading && rightIcon}
    </button>
  );
});
