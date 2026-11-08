import { Link } from 'react-router';
import type { SubjectCode } from '@/types/subject';
import { SUBJECTS } from '@/components/shared/subjects';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/cn';

/**
 * Dizayn: SubjectCard (bd-subj) — telefonda 3 ustunli tik karta, kompyuterda gorizontal.
 * Natija boʻlmasa “15 ta savol” va boʻsh progress, boʻlsa “13/15 toʻgʻri”.
 */
export function SubjectCard({ subject, questionCount, percent, to }: { subject: SubjectCode; questionCount: number; percent: number | null; to: string }) {
  const meta = SUBJECTS[subject];
  const correct = percent === null ? null : Math.round((percent / 100) * questionCount);
  const metaText = correct === null ? `${questionCount} ta savol` : `${correct}/${questionCount} toʻgʻri`;
  return (
    <Link
      to={to}
      className={cn('bd-subj bd-tap tap-card no-underline lg:flex-row! lg:items-center lg:gap-3! lg:p-4! lg:min-h-0!', meta.tone)}
      aria-label={`${meta.short}, ${metaText}, ${Math.round(percent ?? 0)}%`}
    >
      <span className="bd-tile lg:size-10! lg:rounded-[12px]!">
        <Icon name={meta.icon} size={20} />
      </span>
      <span className="flex min-w-0 grow flex-col gap-1.5 lg:gap-1">
        <span className="bd-subj__name">{meta.short}</span>
        <span className="bd-subj__meta">{metaText}</span>
        <span className="bd-bar mt-auto">
          <i style={{ ['--p' as string]: Math.round(percent ?? 0) }} />
        </span>
      </span>
    </Link>
  );
}
