import { memo, useEffect, useReducer, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { Icon } from '@/components/ui/Icon';
import type { MemoryContent } from '../../types';
import type { GameEngineProps } from '../types';
import { initMemory, isMemoryComplete, memoryReducer, type MemoryCard } from './memoryEngine';
import { faceOf } from './faces';
import { GameHeader, GameProgress, GameTimer } from '../../components/GameHeader';
import { FinishingOverlay } from '../../components/FinishingOverlay';
import { cn } from '@/lib/cn';

const MISMATCH_MS = 950;

const CardView = memo(function CardView({ card, index, onFlip }: { card: MemoryCard; index: number; onFlip: (id: string) => void }) {
  const face = faceOf(card.face);
  const Icon = face.icon;
  const up = card.status !== 'hidden';
  const label = card.status === 'hidden' ? `${index + 1}-karta, yopiq` : card.status === 'matched' ? `${face.label}, topildi` : face.label;

  return (
    <button
      type="button"
      onClick={() => onFlip(card.id)}
      aria-label={label}
      aria-disabled={card.status !== 'hidden'}
      className="tap-card relative aspect-[3/4] w-full [perspective:800px] focus-visible:outline-offset-4"
    >
      <motion.span
        className="absolute inset-0 block"
        style={{ transformStyle: 'preserve-3d' }}
        initial={false}
        animate={{ rotateY: up ? 180 : 0, scale: card.status === 'matched' ? [1, 1.06, 1] : 1 }}
        transition={{ duration: 0.38, ease: 'easeOut' }}
      >
        {/* back */}
        <span
          className="absolute inset-0 flex items-center justify-center overflow-hidden rounded-[var(--radius-md)] bg-hero shadow-[0_3px_0_var(--hero-strong)] active:brightness-95"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <svg viewBox="0 0 60 80" className="absolute inset-0 h-full w-full opacity-15" aria-hidden="true" preserveAspectRatio="xMidYMid slice">
            <circle cx="10" cy="12" r="8" fill="#fff" />
            <circle cx="52" cy="70" r="12" fill="#fff" />
            <rect x="38" y="8" width="12" height="12" rx="3" fill="#fff" transform="rotate(15 44 14)" />
          </svg>
          <span className="relative text-[28px] font-black text-white/90">?</span>
        </span>
        {/* front */}
        <span
          className={cn('absolute inset-0 flex items-center justify-center rounded-[var(--radius-md)] border-[2.5px]', card.status === 'matched' ? 'border-success' : 'border-transparent')}
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', background: face.bg }}
        >
          <Icon className="size-[48%]" style={{ color: face.color }} strokeWidth={2.2} aria-hidden="true" />
          {card.status === 'matched' && (
            <span className="absolute top-1.5 right-1.5 flex size-5 items-center justify-center rounded-full bg-success text-white">
              <Icon name="check" size={14} />
            </span>
          )}
        </span>
      </motion.span>
    </button>
  );
});

export default function MemoryGame({ content, title, onExit, onFinish, finishing, finishError }: GameEngineProps<MemoryContent>) {
  const [state, dispatch] = useReducer(memoryReducer, content.cards, initMemory);
  const [startedAt] = useState(() => Date.now());
  const done = isMemoryComplete(state);

  // Close a mismatched pair after a short look.
  useEffect(() => {
    if (state.last !== 'miss' || state.open.length !== 2) return;
    const t = window.setTimeout(() => dispatch({ type: 'hideMismatch' }), MISMATCH_MS);
    return () => window.clearTimeout(t);
  }, [state.last, state.open]);

  // Let the last pair's animation play, then hand the move log to the backend (once).
  const finishRef = useRef(onFinish);
  finishRef.current = onFinish;
  const movesRef = useRef(state.moves);
  movesRef.current = state.moves;
  useEffect(() => {
    if (!done) return;
    const t = window.setTimeout(() => finishRef.current({ moves: movesRef.current }), 700);
    return () => window.clearTimeout(t);
  }, [done]);

  const announce = state.last === 'match' ? 'Juft topildi!' : state.last === 'miss' ? 'Bir xil emas. Joylarini eslab qol.' : '';
  const cols = state.totalPairs <= 6 ? 'grid-cols-4 max-w-[440px]' : 'grid-cols-4 max-w-[480px]';

  return (
    <div className="flex min-h-dvh flex-col">
      <GameHeader
        title={title}
        onExit={onExit}
        right={<GameTimer startedAt={startedAt} running={!done} />}
        progress={<GameProgress value={state.matchedPairs} max={state.totalPairs} label={`${state.totalPairs} ta juftdan ${state.matchedPairs} tasi topildi`} />}
      />

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center px-4 pt-4 pb-[max(24px,env(safe-area-inset-bottom))]">
        <div className="t-sm mb-4 flex w-full max-w-[480px] items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-muted">
            <Icon name="target" size={18} />
            Urinishlar: <span className="tabular text-ink">{state.moves.length}</span>
          </span>
          <span className="text-muted">
            Juftlar: <span className="tabular text-ink">{state.matchedPairs}</span>/{state.totalPairs}
          </span>
        </div>

        <div className={cn('grid w-full gap-2.5 sm:gap-3', cols)}>
          {state.cards.map((card, i) => (
            <CardView key={card.id} card={card} index={i} onFlip={(id) => dispatch({ type: 'flip', id })} />
          ))}
        </div>

        <p aria-live="polite" className="t-h3 mt-5 min-h-6 text-center text-brand-ink">
          {done ? 'Barcha juftlar topildi!' : announce}
        </p>
      </main>

      {done && <FinishingOverlay finishing={finishing} error={finishError} onRetry={() => onFinish({ moves: state.moves })} />}
    </div>
  );
}
