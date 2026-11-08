import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';
import { Icon } from './Icon';
import { cn } from '@/lib/cn';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox({ label, className, id, ...rest }, ref) {
  return (
    <label
      htmlFor={id}
      className={cn(
        'flex min-h-14 cursor-pointer items-center gap-3 rounded-[var(--radius-md)] bg-card px-4 py-3 shadow-[inset_0_0_0_1.5px_var(--line)] transition-colors',
        'has-[:checked]:bg-brand-soft has-[:checked]:shadow-[inset_0_0_0_1.5px_var(--brand)] has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus has-[:focus-visible]:outline-offset-2',
        className,
      )}
    >
      <input ref={ref} id={id} type="checkbox" className="peer sr-only" {...rest} />
      <span
        aria-hidden="true"
        className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-card text-transparent shadow-[inset_0_0_0_2px_var(--ink-3)] transition-colors peer-checked:bg-brand peer-checked:text-on-brand peer-checked:shadow-none"
      >
        <Icon name="check" size={18} />
      </span>
      <span className="text-[15px] font-bold">{label}</span>
    </label>
  );
});
