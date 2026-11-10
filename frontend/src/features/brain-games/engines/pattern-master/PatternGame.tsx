import { LayoutGroup, motion } from 'motion/react';
import { Icon } from '@/components/ui/Icon';
import { StatChip } from '@/components/shared/design';
import type { PatternContent, PatternQuestion } from '../../types';
import type { GameEngineProps } from '../types';
import { useQuizRound } from '../../hooks/useQuizRound';
import { GameHeader, GameProgress } from '../../components/GameHeader';
import { QuizFeedbackPanel } from '../../components/QuizFeedbackPanel';
import { FinishingOverlay } from '../../components/FinishingOverlay';
import { ShapeGlyph, describeShape } from './ShapeGlyph';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';

type Verdict = 'pending' | 'correct' | 'wrong' | null;

/** The pattern as tiles on a track; wraps to two rows on phones so every tile stays big. */
function PatternTrack({ q, chosen, verdict }: { q: PatternQuestion; chosen: PatternQuestion['options'][number] | null; verdict: Verdict }) {
  return (
    <ol className="mx-auto grid w-full max-w-md grid-cols-4 gap-2 sm:max-w-2xl sm:grid-cols-7 sm:gap-2.5" aria-label="Shakllar qatori">
      {q.sequence.map((s, i) =>
        s ? (
          <motion.li
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="aspect-square rounded-[var(--radius-md)] bg-card p-1.5 shadow-[var(--shadow-sm)]"
          >
            <ShapeGlyph shape={s} className="h-full w-full" />
          </motion.li>
        ) : (
          <li key={i} className="aspect-square" aria-label={chosen ? `tanlangan: ${describeShape(chosen.shape)}` : 'keyingi shakl — ?'}>
            {chosen ? (
              <motion.span
                layoutId={`pt-${chosen.id}`}
                className={cn(
                  'block h-full w-full rounded-[var(--radius-md)] p-1.5 ring-[2.5px]',
                  verdict === 'correct' ? 'bg-success-soft ring-success' : verdict === 'wrong' ? 'bg-danger-soft ring-danger' : 'bg-brand-soft ring-brand',
                )}
                animate={verdict === 'wrong' ? { x: [0, -6, 6, -4, 4, 0] } : { x: 0 }}
                transition={{ duration: 0.4 }}
              >
                <ShapeGlyph shape={chosen.shape} labelled={false} className="h-full w-full" />
              </motion.span>
            ) : (
              <motion.span
                className="flex h-full w-full items-center justify-center rounded-[var(--radius-md)] border-[2.5px] border-dashed border-brand bg-brand-soft text-[26px] font-black text-brand-ink"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
              >
                ?
              </motion.span>
            )}
          </li>
        ),
      )}
    </ol>
  );
}

export default function PatternGame({ session, content, resumeAnswers, title, onExit, onFinish, finishing, finishError }: GameEngineProps<PatternContent>) {
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
        progress={<GameProgress value={round.answeredCount} max={total} label={`${total} ta naqshdan ${round.answeredCount} tasi bajarildi`} />}
      />

      <LayoutGroup id={q.id}>
        <main key={q.id} className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 pt-5 pb-64">
          <p className="t-sm muted text-center">{round.index + 1}-naqsh · Keyingi shakl qaysi?</p>
          <div className="mt-4">
            <PatternTrack q={q} chosen={chosen} verdict={verdict} />
          </div>

          <div role="group" aria-label="Javob variantlari" className="bd-answers mx-auto mt-7 w-full max-w-md">
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
                  aria-label={isCorrect ? `${describeShape(o.shape)} — toʻgʻri javob` : isChosen && round.feedback ? `${describeShape(o.shape)} — sizning javobingiz, notoʻgʻri` : describeShape(o.shape)}
                  className={cn(
                    'bd-answer tap-card aspect-[4/3] p-3! disabled:opacity-40',
                    isCorrect && 'is-right',
                    isChosen && round.feedback && !round.feedback.correct && 'is-wrong',
                  )}
                >
                  {isChosen ? (
                    <ShapeGlyph shape={o.shape} labelled={false} className="h-full max-h-24 w-auto opacity-25" />
                  ) : (
                    <motion.span layoutId={`pt-${o.id}`} className="block h-full max-h-24">
                      <ShapeGlyph shape={o.shape} labelled={false} className="h-full w-auto" />
                    </motion.span>
                  )}
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
      {(finishing || finishError !== null) && <FinishingOverlay finishing={finishing} error={finishError} onRetry={() => onFinish()} />}
    </div>
  );
}
