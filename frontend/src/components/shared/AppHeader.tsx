import { Link } from 'react-router';
import { useStudent } from '@/features/auth/hooks/useSession';
import { useMotivation } from '@/hooks/useMotivation';
import { Avatar, StatChip, classLabel } from './design';

/**
 * Dizayn: AppHeader — telefonda ixcham (avatar + “Salom, Aziz! 👋” + 🔥/⭐ chiplari, ≤56px),
 * kompyuterda display sarlavha + chiplar + avatar oʻngda.
 */
export function AppHeader({ sub, desktopSub }: { sub?: string; desktopSub?: string }) {
  const student = useStudent();
  const { stars, streak } = useMotivation();
  const subline = sub ?? (classLabel(student.className) || (student.schoolName ?? ''));
  return (
    <>
      {/* telefon / planshet */}
      <header className="bd-head -mx-4 md:-mx-6 lg:hidden">
        <Link to="/profile" aria-label="Profil">
          <Avatar first={student.firstName} last={student.lastName} photoUrl={student.photoUrl} />
        </Link>
        <div className="grow">
          <div className="bd-head__hi truncate">Salom, {student.firstName}! 👋</div>
          {subline && <div className="bd-head__sub truncate">{subline}</div>}
        </div>
        <StatChip kind="streak" label={`Kunlik seriya: ${streak} kun`}>
          {streak}
        </StatChip>
        <StatChip kind="star" label={`Ball: ${stars}`}>
          {stars}
        </StatChip>
      </header>

      {/* kompyuter */}
      <header className="mb-6 hidden items-center justify-between gap-4 lg:flex">
        <div className="min-w-0">
          <h1 className="t-display truncate">Salom, {student.firstName}! 👋</h1>
          <p className="t-body muted">{desktopSub ?? 'Bugun ham bilimlaringni sinab koʻramizmi?'}</p>
        </div>
        <div className="row shrink-0">
          <StatChip kind="streak" label={`Kunlik seriya: ${streak} kun`}>
            {streak} kun
          </StatChip>
          <StatChip kind="star" label={`Ball: ${stars}`}>
            {stars}
          </StatChip>
          <Link to="/profile" aria-label="Profil" className="ml-2">
            <Avatar first={student.firstName} last={student.lastName} photoUrl={student.photoUrl} size={40} />
          </Link>
        </div>
      </header>
    </>
  );
}
