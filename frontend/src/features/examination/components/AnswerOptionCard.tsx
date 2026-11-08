import type { AnswerOption } from '../types';
import { InlineContent } from '@/components/shared/RichContent';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

interface Props {
  name: string;
  option: AnswerOption;
  checked: boolean;
  disabled: boolean;
  onSelect: () => void;
}

/**
 * Dizayn: javob kartasi (bd-answer uslubi) — 1.5px chiziq + 3px pastki qirra, bosilganda pastga tushadi.
 * Butun karta bosiladi; native radio ustiga qurilgan (strelkalar, fokus, screen reader bepul).
 * Tanlov chegarasi + fon + ✓ belgisi bilan koʻrsatiladi — faqat rang bilan emas.
 */
export function AnswerOptionCard({ name, option, checked, disabled, onSelect }: Props) {
  return (
    <label
      className={cn(
        'tap-card group relative flex min-h-16 cursor-pointer items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 transition-[background-color,transform,box-shadow] duration-150 md:gap-3.5 md:px-3.5',
        'active:translate-y-0.5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus',
        checked
          ? 'bg-brand-soft shadow-[inset_0_0_0_2px_var(--brand),0_3px_0_var(--brand)]'
          : 'bg-card shadow-[inset_0_0_0_1.5px_var(--line),0_3px_0_var(--line)] hover:bg-bg-tint',
        disabled && 'cursor-default opacity-70 active:translate-y-0',
      )}
    >
      <input type="radio" name={name} value={option.id} checked={checked} disabled={disabled} onChange={onSelect} className="sr-only" />
      <span
        aria-hidden="true"
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[15px] font-black transition-colors',
          checked ? 'bg-brand text-on-brand' : 'bg-bg-tint text-brand-ink',
        )}
      >
        {checked ? <Icon name="check" size={18} /> : option.label}
      </span>
      <span className="min-w-0 flex-1 text-[16px] leading-snug font-bold md:text-[17px]">
        <span className="sr-only">{option.label}) </span>
        <InlineContent blocks={option.content} displayStyle />
      </span>
    </label>
  );
}
