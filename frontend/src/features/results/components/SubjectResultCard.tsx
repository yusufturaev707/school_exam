import type { SubjectResult } from '../types';
import { subjectMessage } from '../utils/feedback';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { SUBJECTS, SubjectIcon } from '@/components/shared/subjects';
import { cn } from '@/lib/cn';

export function SubjectResultCard({ result }: { result: SubjectResult }) {
  const meta = SUBJECTS[result.subject];
  const pct = Math.round(result.percent);
  return (
    <li className={cn('bd-card flex flex-col gap-3 p-4!', meta.tone)}>
      <div className="row gap-3!">
        <SubjectIcon subject={result.subject} />
        <div className="grow">
          <h3 className="t-h3">{meta.title}</h3>
          <p className="t-xs faint tabular">
            {result.correct} / {result.total} toʻgʻri · {result.incorrect} xato · {result.unanswered} javobsiz
          </p>
        </div>
        <span className={cn('t-stat tabular', meta.ink)}>{pct}%</span>
      </div>
      <ProgressBar value={result.correct} max={result.total} label={`${meta.title}: ${result.total} tadan ${result.correct} ta toʻgʻri`} />
      <p className={cn('t-sm rounded-[var(--radius-md)] p-3', meta.bg, meta.ink)}>{subjectMessage(result.subject, result.percent)}</p>
    </li>
  );
}
