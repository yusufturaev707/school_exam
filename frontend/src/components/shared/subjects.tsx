import type { SubjectCode } from '@/types/subject';
import { Icon, type IconName } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

export interface SubjectMeta {
  title: string;
  short: string;
  description: string;
  icon: IconName;
  /** Dizayn rang toʻplami: `is-math` / `is-logic` / `is-lang` (--c, --cs, --ci ni oʻrnatadi). */
  tone: string;
  /** Yumshoq fon (plita). */
  bg: string;
  /** Matn rangi — `bg` va `card` ustida AA. */
  ink: string;
  /** Toʻyingan rang (progress). */
  bar: string;
}

export const SUBJECTS: Record<SubjectCode, SubjectMeta> = {
  math: {
    title: 'Matematika',
    short: 'Matematika',
    description: 'Sonlar, ifodalar va shakllar',
    icon: 'sigma',
    tone: 'is-math',
    bg: 'bg-math-soft',
    ink: 'text-math-ink',
    bar: 'bg-math-solid',
  },
  iq: {
    title: 'Mantiq (IQ)',
    short: 'Mantiq (IQ)',
    description: 'Naqshlar, ketma-ketliklar va jumboqlar',
    icon: 'puzzle',
    tone: 'is-logic',
    bg: 'bg-logic-soft',
    ink: 'text-logic-ink',
    bar: 'bg-logic',
  },
  language: {
    // Bitta nom hamma joyda (bosh sahifa, filtrlar, natija kartasi) — backenddagi boʻlim nomi koʻrsatilmaydi.
    title: 'Ona tili',
    short: 'Ona tili',
    description: 'Ona tili va adabiyot: oʻqish, grammatika va soʻz boyligi',
    icon: 'book',
    tone: 'is-lang',
    bg: 'bg-lang-soft',
    ink: 'text-lang-ink',
    bar: 'bg-lang',
  },
};

export const SUBJECT_ORDER: SubjectCode[] = ['math', 'iq', 'language'];

/** Dizayn: bd-tile — `sm` 28px, `md` 32px (standart), `lg` 40px. */
export function SubjectIcon({ subject, size = 'md', className }: { subject: SubjectCode; size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const meta = SUBJECTS[subject];
  return (
    <span aria-hidden="true" className={cn('bd-tile', meta.tone, size === 'sm' && 'size-7!', size === 'lg' && 'bd-tile--lg', className)}>
      <Icon name={meta.icon} size={size === 'sm' ? 16 : size === 'lg' ? 22 : 20} />
    </span>
  );
}
