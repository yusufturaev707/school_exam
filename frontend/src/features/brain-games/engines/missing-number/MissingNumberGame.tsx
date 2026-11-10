import { LayoutGroup, motion } from 'motion/react';
import { Icon } from '@/components/ui/Icon';
import { StatChip } from '@/components/shared/design';
import type { MissingNumberContent, MissingNumberQuestion } from '../../types';
import type { GameEngineProps } from '../types';
import { useQuizRound } from '../../hooks/useQuizRound';
import { GameHeader, GameProgress } from '../../components/GameHeader';
import { QuizFeedbackPanel } from '../../components/QuizFeedbackPanel';
import { FinishingOverlay } from '../../components/FinishingOverlay';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';

const digitsClass = (n: number) => (String(n).length >= 4 ? 'text-[18px]' : String(n).length === 3 ? 'text-[21px]' : 'text-[26px]');

type Verdict = 'pending' | 'correct' | 'wrong' | null;

/** The sequence as a little train of number wagons on a rail; the hidden wagon is the "?" slot. */
function NumberTrain({ q, chosenValue, chosenId, verdict }: { q: MissingNumberQuestion; chosenValue: number | null; chosenId: string | null; verdict: Verdict }) {
  return (
    <div className="relative mx-auto w-full max-w-md">
      <div className="absolute inset-x-2 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-line" aria-hidden="true" />
      <ol className="relative grid grid-cols-5 gap-1.5 sm:gap-2.5" aria-label="Sonlar qatori">
        {q.sequence.map((v, i) =>
          v === null ? (
            <li key={i} className="aspect-square" aria-label={chosenValue === null ? 'yashiringan son' : `tanlangan son ${chosenValue}`}>
              {chosenValue === null || !chosenId ? (
                <motion.span
                  className="flex h-full w-full items-center justify-center rounded-[var(--radius-md)] border-[2.5px] border-dashed border-brand bg-brand-soft text-[26px] font-black text-brand-ink"
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
                >
                  ?
                </motion.span>
              ) : (
                <motion.span
                  layoutId={`mn-${chosenId}`}
                  className={cn(
                    'tabular flex h-full w-full items-center justify-center rounded-[var(--radius-md)] font-black text-white shadow-md',
                    digitsClass(chosenValue),
                    verdict === 'correct' ? 'bg-success' : verdict === 'wrong' ? 'bg-danger' : 'bg-brand',
                  )}
                  animate={verdict === 'wrong' ? { x: [0, -6, 6, -4, 4, 0] } : { x: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  {chosenValue}
                </motion.span>
              )}
            </li>
          ) : (
            <li key={i} className={cn('tabular flex aspect-square items-center justify-center rounded-[var(--radius-md)] bg-card font-black text-ink shadow-[var(--shadow-sm)]', digitsClass(v))}>
              {v}
            </li>
          ),
        )}
      </ol>
    </div>
  );
}

export default function MissingNumberGame({ session, content, resumeAnswers, title, onExit, onFinish, finishing, finishError }: GameEngineProps<MissingNumberContent>) {
  const total = content.questions.length;
  const round = useQuizRound(
    session.id,
    total,
    content.questions.map((q) => q.id),
    resumeAnswers && { answers: resumeAnswers, score: session.score, correct: session.correctAnswers },
  );
  const q = content.questions[round.index]!;
  const verdict: Verdict = round.feedback ? (round.feedback.correct ? 'correct' : 'wrong') : round.pending ? 'pending' : null;
  const chosen = q.options.find((o) => o.id === round.selected) ?? null;
  const showFinish = finishing || finishError !== null;

  return (
    <div className="flex min-h-dvh flex-col">
      <GameHeader
        title={title}
        onExit={onExit}
        right={
          <StatChip kind="star" label={`${round.score} ball`}>
            {round.score}
          </StatChip>
        }
        progress={<GameProgress value={round.answeredCount} max={total} label={`${total} ta savoldan ${round.answeredCount} tasi bajarildi`} />}
      />

      <LayoutGroup id={q.id}>
        <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pt-6 pb-64">
          <p className="t-sm muted text-center">
            {round.index + 1}-topshiriq · Qaysi son yashiringan?
          </p>
          <div className="mt-5">
            <NumberTrain q={q} chosenValue={chosen?.value ?? null} chosenId={chosen?.id ?? null} verdict={verdict} />
          </div>

          <div role="group" aria-label="Javob variantlari" className="bd-answers mt-8">
            {q.options.map((o) => {
              const isChosen = o.id === round.selected;
              const isCorrect = round.feedback?.correctOptionId === o.id;
              const locked = round.feedback !== null || round.pending;
              return (
                <button
                  key={o.id}
                  type="button"
                  onClick={() => round.choose(q.id, o.id)}
                  disabled={locked && !isChosen && !isCorrect}
                  aria-pressed={isChosen}
                  aria-label={isCorrect ? `${o.value} — toʻgʻri javob` : isChosen && round.feedback ? `${o.value} — sizning javobingiz, notoʻgʻri` : `Javob: ${o.value}`}
                  className={cn(
                    'bd-answer bd-answer--lg tap-card text-[26px]! disabled:opacity-45',
                    isCorrect && 'is-right',
                    isChosen && round.feedback && !round.feedback.correct && 'is-wrong',
                  )}
                >
                  {/* the chosen number "flies" into the train slot */}
                  {isChosen ? <span className="tabular opacity-30">{o.value}</span> : <motion.span layoutId={`mn-${o.id}`} className="tabular">{o.value}</motion.span>}
                  {isChosen && round.pending && <Spinner className="absolute top-2 right-2 size-4 text-brand" />}
                  {isCorrect && <Icon name="check" size={18} className="absolute top-1.5 right-2 text-success" />}
                  {isChosen && round.feedback && !round.feedback.correct && <Icon name="x" size={18} className="absolute top-1.5 right-2 text-danger" />}
                </button>
              );
            })}
          </div>
        </main>
      </LayoutGroup>

      <QuizFeedbackPanel feedback={round.feedback} error={round.error} isLast={round.isLast} onNext={round.isLast ? () => onFinish() : round.next} />
      {showFinish && <FinishingOverlay finishing={finishing} error={finishError} onRetry={() => onFinish()} />}
    </div>
  );
}
