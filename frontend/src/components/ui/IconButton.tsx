import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required: icon-only buttons must have an accessible name. */
  label: string;
  icon: ReactNode;
  variant?: 'soft' | 'ghost' | 'solid';
}

/** Dizayn: bd-iconbtn — 36px, hit-area 44px. `soft` — karta foni + soya. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, icon, variant = 'ghost', className, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        'bd-iconbtn transition-[transform,background-color] active:scale-95 disabled:opacity-50',
        variant === 'soft' && 'bd-iconbtn--soft',
        variant === 'ghost' && 'hover:bg-bg-tint',
        variant === 'solid' && 'bg-brand text-on-brand',
        className,
      )}
      {...rest}
    >
      {icon}
    </button>
  );
});
