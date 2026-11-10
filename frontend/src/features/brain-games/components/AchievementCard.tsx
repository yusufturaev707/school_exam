import { useState } from 'react';
import type { Achievement } from '../types';
import { achievementIcon, achievementTone } from '../utils/meta';
import { Icon } from '@/components/ui/Icon';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { formatDay } from '@/lib/date';
import { cn } from '@/lib/cn';

/** Olinganlar → ochiq qolganlar → “Tez orada” (hali oʻynab boʻlmaydiganlar) — oxirida. */
export function sortAchievements(list: Achievement[]) {
  const rank = (a: Achievement) => (a.unlockedAt ? 0 : a.comingSoon ? 2 : 1);
  return [...list].sort((a, b) => rank(a) - rank(b));
}

/** “2/6” hisobi faqat hozir olish mumkin boʻlgan nishonlar boʻyicha. */
export function badgeSummary(list: Achievement[] | undefined) {
  const all = list ?? [];
  return { unlocked: all.filter((a) => a.unlockedAt).length, available: all.filter((a) => a.unlockedAt || !a.comingSoon).length };
}

function statusText(a: Achievement) {
  if (a.unlockedAt) return 'olingan';
  if (a.comingSoon) return 'tez orada';
  return `${Math.min(a.progress.current, a.progress.target)} / ${a.progress.target}`;
}

/** Nishon tafsiloti: sharti, progress yoki olingan sana. */
function AchievementDialog({ achievement: a, open, onClose }: { achievement: Achievement; open: boolean; onClose: () => void }) {
  const { current, target } = a.progress;
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={a.title}
      description={a.description}
      footer={
        <Button variant="secondary" fullWidth onClick={onClose} aria-label="Nishon oynasini yopish">
          Tushunarli
        </Button>
      }
    >
      <div className={cn('row gap-3!', achievementTone(a.icon), !a.unlockedAt && 'is-muted')}>
        <span className="bd-badge__disc size-14! shrink-0" style={a.unlockedAt ? undefined : { background: 'var(--bg-tint)', color: 'var(--ink-3)' }}>
          <Icon name={achievementIcon(a.icon)} size={26} />
        </span>
        <div className="grow">
          {a.unlockedAt ? (
            <p className="t-h3 text-success-ink">✓ {formatDay(a.unlockedAt)} da olingan</p>
          ) : a.comingSoon ? (
            <>
              <span className="bd-chip bd-chip--soft">
                <Icon name="lock" size={14} />
                Tez orada
              </span>
              <p className="t-sm muted mt-1">Bu nishonni beradigan oʻyinlar hali tayyorlanmoqda. Ular chiqqach, uni ochishingiz mumkin.</p>
            </>
          ) : (
            <>
              <div className="row justify-between">
                <span className="t-sm muted">Progress</span>
                <b className="t-sm tabular">
                  {Math.min(current, target)} / {target}
                </b>
              </div>
              <ProgressBar value={Math.min(current, target)} max={target} label={`${a.title}: ${current} / ${target}`} className="mt-1.5" />
            </>
          )}
        </div>
      </div>
    </Modal>
  );
}

/**
 * Dizayn: Badge (bd-badge) — 52px disk, qulflangan holatda kulrang + qulf. Bosilsa — shart va progress.
 * `compact` — bosh sahifadagi 4 nishonli qator; aks holda 3 ustunli gridda progress yoki “✓ Olingan”.
 * Qulflangan nishon hech qachon “muvaffaqiyatsiz” deb koʻrsatilmaydi — faqat doʻstona progress.
 */
export function AchievementCard({ achievement, compact = false }: { achievement: Achievement; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const unlocked = achievement.unlockedAt !== null;
  const { current, target } = achievement.progress;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`${achievement.title} nishoni, ${statusText(achievement)}. Batafsil`}
        className={cn('bd-badge bd-tap tap-card', achievementTone(achievement.icon), !unlocked && 'is-locked', achievement.comingSoon && 'opacity-70')}
      >
        <span className="bd-badge__disc">
          <Icon name={achievementIcon(achievement.icon)} size={24} />
          {!unlocked && (
            <span className="bd-badge__lock">
              <Icon name="lock" size={12} />
            </span>
          )}
        </span>
        <span className="bd-badge__name">{achievement.title}</span>
        {compact ? null : unlocked ? (
          <span className="t-xs text-success-ink">✓ Olingan</span>
        ) : achievement.comingSoon ? (
          <span className="t-xs faint">Tez orada</span>
        ) : (
          <span className="t-xs faint tabular">
            {Math.min(current, target)}/{target}
          </span>
        )}
      </button>
      <AchievementDialog achievement={achievement} open={open} onClose={() => setOpen(false)} />
    </>
  );
}

/** Bosh sahifa: 4 ta nishon qatori (olish mumkin boʻlganlari birinchi). */
export function BadgeRow({ achievements }: { achievements: Achievement[] }) {
  return (
    <div className="bd-badges">
      {sortAchievements(achievements)
        .slice(0, 4)
        .map((a) => (
          <AchievementCard key={a.id} achievement={a} compact />
        ))}
    </div>
  );
}
