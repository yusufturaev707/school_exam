import { Link } from 'react-router';
import { useState, type ReactNode } from 'react';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { badgeSummary } from '@/features/brain-games/components/AchievementCard';
import { useLogout, useStudent } from '@/features/auth/hooks/useSession';
import { useAchievements, useGameStatistics } from '@/features/brain-games/hooks/useGames';
import { CATEGORY_META } from '@/features/brain-games/utils/meta';
import { useResults } from '@/features/results/api/resultsApi';
import { Button } from '@/components/ui/Button';
import { Icon, type IconName } from '@/components/ui/Icon';
import { Avatar, Section, StatTile, StatTiles, classLabel } from '@/components/shared/design';
import { useMotivation } from '@/hooks/useMotivation';
import { useTheme } from '@/lib/theme';
import { cn } from '@/lib/cn';

/** Daraja — faqat oʻz ballaringdan hisoblanadi (har 150 ⭐ — yangi daraja). */
const LEVEL_STEP = 150;
const LEVEL_NAMES = ['Yangi kashfiyotchi', 'Qiziquvchan', 'Izlanuvchi', 'Bilimdon-izlanuvchi', 'Kichik olim', 'Bilimdon'];
export function levelOf(stars: number) {
  const level = Math.floor(stars / LEVEL_STEP) + 1;
  return { level, name: LEVEL_NAMES[Math.min(level - 1, LEVEL_NAMES.length - 1)]!, into: stars % LEVEL_STEP, step: LEVEL_STEP, next: level * LEVEL_STEP };
}

function Row({ to, icon, label, onClick, right, checked }: { to?: string; icon: IconName; label: string; onClick?: () => void; right?: ReactNode; checked?: boolean }) {
  const inner = (
    <>
      <span className="bd-tile">
        <Icon name={icon} size={18} />
      </span>
      <span className="t-h3 grow text-left">{label}</span>
      {right ?? <Icon name="chevR" size={18} className="text-ink-3" />}
    </>
  );
  const cls = 'bd-rowcard tap-card min-h-12 w-full py-2 text-inherit no-underline';
  return (
    <li className="p-0!">
      {to ? (
        <Link to={to} className={cls}>
          {inner}
        </Link>
      ) : (
        <button type="button" onClick={onClick} className={cls} role={checked !== undefined ? 'switch' : undefined} aria-checked={checked}>
          {inner}
        </button>
      )}
    </li>
  );
}

/** Dizayn: ScreenResultsProfile → “Profil”: daraja + XP, seriya, eng yaxshi natijalar, sozlamalar. */
export default function ProfilePage() {
  const student = useStudent();
  const logout = useLogout();
  const { stars, streak } = useMotivation();
  const achievements = useAchievements();
  const stats = useGameStatistics();
  const results = useResults();
  const { dark, setTheme } = useTheme();
  const lvl = levelOf(stars);
  const { unlocked, available } = badgeSummary(achievements.data);
  const [confirmLogout, setConfirmLogout] = useState(false);

  const bestExam = results.data?.length ? [...results.data].sort((a, b) => b.percent - a.percent)[0] : undefined;
  const bestGames = (stats.data?.games ?? [])
    .filter((g) => g.bestScore !== null)
    .sort((a, b) => (b.bestScore ?? 0) - (a.bestScore ?? 0))
    .slice(0, bestExam ? 2 : 3);

  return (
    <div className="lg:grid lg:grid-cols-[1fr_1fr] lg:items-start lg:gap-6">
      <div>
        <div className="bd-card relative mt-2 overflow-hidden p-4! text-center lg:mt-0">
          <div className="absolute inset-x-0 top-0 h-14 bg-brand-soft" aria-hidden="true" />
          <Avatar first={student.firstName} last={student.lastName} photoUrl={student.photoUrl} size={72} className="relative mx-auto mt-2 shadow-[0_0_0_4px_var(--card)]!" />
          <h1 className="t-hero mt-2">
            {student.firstName} {student.lastName}
          </h1>
          {(student.className || student.schoolName) && (
            <p className="t-sm muted">{[classLabel(student.className), student.schoolName].filter(Boolean).join(' · ')}</p>
          )}
          <div className="row mt-3 gap-2.5! text-left">
            <span className="bd-chip bd-chip--stat is-brand">
              <Icon name="trophy" size={16} />
              {lvl.level}-daraja
            </span>
            <div className="grow">
              <div className="row justify-between">
                <span className="t-xs muted">{lvl.name}</span>
                <span className="t-xs tabular">
                  {stars} / {lvl.next} ⭐
                </span>
              </div>
              <span className="bd-bar mt-1 block" role="progressbar" aria-label="Keyingi darajagacha" aria-valuemin={0} aria-valuemax={lvl.step} aria-valuenow={lvl.into}>
                <i style={{ ['--p' as string]: Math.round((lvl.into / lvl.step) * 100) }} />
              </span>
            </div>
          </div>
        </div>

        <StatTiles className="mt-3">
          <StatTile icon="fire" value={streak} label="kun seriya" tone="is-streak" />
          <StatTile icon="star" value={stars} label="ball" tone="is-star" />
          <StatTile icon="trophy" value={achievements.data ? `${unlocked}/${available}` : '–'} label="yutuq" tone="is-memory" />
        </StatTiles>

        {(bestExam || bestGames.length > 0) && (
          <Section title="Eng yaxshi natijalar" id="best-title">
            <ul className="bd-card bd-list px-4! py-0.5!">
              {bestExam && (
                <li className="p-0!">
                  <Link to={`/results/${bestExam.id}`} className="bd-rowcard is-brand tap-card min-h-12 py-2 text-inherit no-underline">
                    <span className="bd-tile">
                      <Icon name="exam" />
                    </span>
                    <span className="t-h3 grow truncate">{bestExam.examTitle}</span>
                    <b className="t-h3 tabular">
                      {bestExam.correct}/{bestExam.total}
                    </b>
                  </Link>
                </li>
              )}
              {bestGames.map((g) => (
                <li key={g.gameId} className="p-0!">
                  <Link
                    to={`/activities/play/${g.slug}`}
                    aria-label={`${g.title}: eng yaxshi natija ${g.bestScore} ball. Yana oʻynash`}
                    className={cn('bd-rowcard tap-card min-h-12 py-2 text-inherit no-underline', CATEGORY_META[g.category].tone)}
                  >
                    <span className="bd-tile">
                      <Icon name={CATEGORY_META[g.category].icon} />
                    </span>
                    <span className="t-h3 grow truncate">{g.title}</span>
                    <b className="t-h3 tabular">{g.bestScore} ⭐</b>
                    <Icon name="chevR" size={18} className="text-ink-3" />
                  </Link>
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>

      <div>
        <Section title="Sozlamalar" id="settings-title" className="lg:mt-0">
          <ul className="bd-card bd-list px-4! py-0.5!">
            <Row
              icon="moon"
              label="Qorongʻi rejim"
              onClick={() => setTheme(dark ? 'light' : 'dark')}
              checked={dark}
              right={
                <span
                  aria-hidden="true"
                  className={cn('relative h-7 w-12 shrink-0 rounded-full transition-colors', dark ? 'bg-brand' : 'bg-line')}
                >
                  <span className={cn('absolute top-1 size-5 rounded-full bg-card shadow-sm transition-[left]', dark ? 'left-6' : 'left-1')} />
                </span>
              }
            />
            <Row to="/results" icon="history" label="Imtihonlar tarixi" />
            <Row to="/activities/achievements" icon="trophy" label="Yutuqlarim" />
            <Row to="/help" icon="help" label="Yordam" />
            <Row to="/help#privacy" icon="shield" label="Maxfiylik" />
          </ul>
        </Section>

        <p className="t-xs faint mt-3 text-center">Shaxsiy maʼlumotlarni faqat maktabing oʻzgartiradi.</p>
        <Button
          variant="ghost"
          fullWidth
          className="mt-1 text-danger-ink! hover:bg-danger-soft!"
          aria-label="Hisobdan chiqish"
          onClick={() => setConfirmLogout(true)}
          leftIcon={<Icon name="logout" />}
        >
          Chiqish
        </Button>
        <ConfirmationDialog
          open={confirmLogout}
          title="Hisobdan chiqasanmi?"
          description="Keyingi safar kirish uchun yana QR kod yoki JSHSHIR kerak boʻladi. Natijalaring saqlanib qoladi."
          confirmLabel="Ha, chiqish"
          cancelLabel="Qolish"
          loading={logout.isPending}
          onCancel={() => setConfirmLogout(false)}
          onConfirm={() => logout.mutate()}
        />
      </div>
    </div>
  );
}
